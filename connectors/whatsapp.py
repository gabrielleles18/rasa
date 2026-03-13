import hashlib
import hmac
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Text

import aiohttp
from sanic import Blueprint, response
from sanic.request import Request

from rasa.core.channels.channel import InputChannel, OutputChannel, UserMessage

logger = logging.getLogger(__name__)

WHATSAPP_API_URL = "https://graph.facebook.com/v21.0"


class WhatsAppOutput(OutputChannel):
    """Output channel para enviar mensagens via WhatsApp Cloud API."""

    @classmethod
    def name(cls) -> Text:
        return "whatsapp"

    def __init__(self, phone_number_id: Text, access_token: Text) -> None:
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.api_url = f"{WHATSAPP_API_URL}/{phone_number_id}/messages"

    async def _send_message(self, recipient_id: Text, payload: Dict) -> None:
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        body = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            **payload,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.api_url, json=body, headers=headers
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(
                        "Erro ao enviar mensagem WhatsApp: %s %s", resp.status, text
                    )

    async def send_text_message(
        self, recipient_id: Text, text: Text, **kwargs: Any
    ) -> None:
        await self._send_message(recipient_id, {"type": "text", "text": {"body": text}})

    async def send_image_url(
        self, recipient_id: Text, image: Text, **kwargs: Any
    ) -> None:
        await self._send_message(
            recipient_id,
            {"type": "image", "image": {"link": image}},
        )

    async def send_text_with_buttons(
        self,
        recipient_id: Text,
        text: Text,
        buttons: List[Dict[Text, Any]],
        **kwargs: Any,
    ) -> None:
        interactive_buttons = []
        for i, btn in enumerate(buttons[:3]):
            interactive_buttons.append(
                {
                    "type": "reply",
                    "reply": {
                        "id": btn.get("payload", str(i)),
                        "title": btn.get("title", "")[:20],
                    },
                }
            )

        await self._send_message(
            recipient_id,
            {
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": text},
                    "action": {"buttons": interactive_buttons},
                },
            },
        )


class WhatsAppInput(InputChannel):
    """Canal de entrada para receber mensagens do WhatsApp Cloud API."""

    @classmethod
    def name(cls) -> Text:
        return "whatsapp"

    @classmethod
    def from_credentials(cls, credentials: Optional[Dict[Text, Any]]) -> "WhatsAppInput":
        if not credentials:
            cls.raise_missing_credentials_exception()
        return cls(
            credentials.get("phone_number_id"),
            credentials.get("access_token"),
            credentials.get("verify_token"),
            credentials.get("app_secret"),
        )

    def __init__(
        self,
        phone_number_id: Text,
        access_token: Text,
        verify_token: Text,
        app_secret: Optional[Text] = None,
    ) -> None:
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.verify_token = verify_token
        self.app_secret = app_secret

    def _validate_signature(self, payload: bytes, signature: Text) -> bool:
        if not self.app_secret:
            return True
        expected = hmac.new(
            self.app_secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)

    @staticmethod
    def _extract_message(body: Dict) -> Optional[Dict[Text, Any]]:
        try:
            entry = body["entry"][0]
            changes = entry["changes"][0]
            value = changes["value"]
            messages = value.get("messages")
            if not messages:
                return None
            return messages[0]
        except (KeyError, IndexError):
            return None

    @staticmethod
    def _get_text(message: Dict) -> Optional[Text]:
        msg_type = message.get("type")
        if msg_type == "text":
            return message.get("text", {}).get("body")
        if msg_type == "interactive":
            interactive = message.get("interactive", {})
            reply = interactive.get("button_reply") or interactive.get("list_reply")
            if reply:
                return reply.get("title") or reply.get("id")
        return None

    def get_output_channel(self) -> WhatsAppOutput:
        return WhatsAppOutput(self.phone_number_id, self.access_token)

    def blueprint(
        self, on_new_message: Callable[[UserMessage], Awaitable[None]]
    ) -> Blueprint:
        whatsapp_webhook = Blueprint("whatsapp_webhook", __name__)

        @whatsapp_webhook.route("/", methods=["GET"])
        async def health(request: Request):
            return response.json({"status": "ok"})

        @whatsapp_webhook.route("/webhook", methods=["GET"])
        async def verify(request: Request):
            mode = request.args.get("hub.mode")
            token = request.args.get("hub.verify_token")
            challenge = request.args.get("hub.challenge")

            if mode == "subscribe" and token == self.verify_token:
                return response.text(challenge)
            return response.text("Forbidden", status=403)

        @whatsapp_webhook.route("/webhook", methods=["POST"])
        async def receive(request: Request):
            if self.app_secret:
                signature = request.headers.get("X-Hub-Signature-256", "")
                if not self._validate_signature(request.body, signature):
                    return response.text("Invalid signature", status=403)

            body = request.json
            message = self._extract_message(body)

            if message:
                sender_id = message.get("from")
                text = self._get_text(message)

                if text and sender_id:
                    out_channel = self.get_output_channel()
                    user_message = UserMessage(
                        text=text,
                        output_channel=out_channel,
                        sender_id=sender_id,
                        input_channel=self.name(),
                    )
                    await on_new_message(user_message)

            return response.text("OK", status=200)

        return whatsapp_webhook
