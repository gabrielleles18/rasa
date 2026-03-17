import re
import logging
from typing import Any, Dict, List, Optional, Text

from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.events import SlotSet, ActiveLoop, FollowupAction, Restarted, AllSlotsReset
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict

logger = logging.getLogger(__name__)

API_BASE_URL = "http://nucleogov-portal/api"

MEDIA_TYPES = ("image", "document", "video", "audio")


def _extrair_midia_whatsapp(tracker: "Tracker") -> Optional[Dict]:
    """Extrai informacoes de midia da mensagem do WhatsApp."""
    metadata = tracker.latest_message.get("metadata", {}) or {}

    for media_type in MEDIA_TYPES:
        media = metadata.get(media_type)
        if media:
            return {
                "tipo": media_type,
                "id": media.get("id"),
                "mime_type": media.get("mime_type"),
                "filename": media.get("filename"),
                "url": media.get("url") or media.get("link"),
                "caption": media.get("caption"),
            }

    image_url = metadata.get("image_url") or metadata.get("attachment")
    if image_url:
        return {"tipo": "image", "url": image_url}

    return None

MENU_OPCOES = "1 - Registrar Manifestação\n2 - Acompanhar Manifestação"
MENU_OPCOES_2 = [
    {"id": 1, "titulo": "Nova Manifestação"},
    {"id": 2, "titulo": "Ver Manifestação"},
    {"id": 3, "titulo": "Sair"},
]

SAUDACOES = {
    "bom dia": "Bom dia!",
    "boa tarde": "Boa tarde!",
    "boa noite": "Boa noite!",
    "oi": "Oi!",
    "ola": "Ola!",
    "oie": "Oi!",
    "hello": "Hello!",
    "hi": "Oi!",
    "hey": "Hey!",
    "eai": "E ai!",
    "e ai": "E ai!",
    "fala": "Fala!",
    "opa": "Opa!",
    "salve": "Salve!",
}


class ActionGreet(Action):
    def name(self) -> Text:
        return "action_greet"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Dict[Text, Any]]:
        msg = (tracker.latest_message.get("text") or "").strip().lower()

        saudacao = "Ola!"
        for chave, resposta in SAUDACOES.items():
            if chave in msg:
                saudacao = resposta
                break
        dispatcher.utter_message(
            json_message={
                "opcoes": MENU_OPCOES_2,
                "mensagem": f"{saudacao} Sou o assistente virtual da Ouvidoria. Como posso ajudar?",
                "tipo_msn": "interactive-reply"
            }
        )
        return []

TIPOS_MANIFESTACAO = [
    {"id": 1, "titulo": "Denúncia"},
    {"id": 2, "titulo": "Reclamação"},
    {"id": 3, "titulo": "Sugestão"},
    {"id": 4, "titulo": "Elogio"},
    {"id": 5, "titulo": "Solicitação"},
]

TIPOS_DOCUMENTO = [
    {"id": 1, "titulo": "CPF"},
    {"id": 2, "titulo": "CNPJ"},
    {"id": 3, "titulo": "RG"},
    {"id": 4, "titulo": "Registro Profissional"},
    {"id": 5, "titulo": "CNH"},
    {"id": 6, "titulo": "Outro"},
]

ASSUNTOS_MANIFESTACAO = [
    {"id": 1, "titulo": "Proteção e Benefícios"},
    {"id": 2, "titulo": "Receita"},
    {"id": 3, "titulo": "Serviços e Sistemas"},
    {"id": 4, "titulo": "Saúde"},
    {"id": 5, "titulo": "Agricultura"},
    {"id": 6, "titulo": "Imposto"},
]

def _resolver_tipo_documento_id(valor: str) -> Optional[int]:
    """Resolve um valor (id ou título) para o id interno do tipo de documento."""
    valor_norm = valor.strip().lower()
    if not valor_norm:
        return None

    for item in TIPOS_DOCUMENTO:
        if str(item["id"]) == valor_norm or item["titulo"].lower() == valor_norm:
            return item["id"]

    return None

def _resolver_assunto_id(valor: str) -> Optional[int]:
    """Resolve um valor (id ou título) para o id interno do assunto."""
    valor_norm = valor.strip().lower()
    if not valor_norm:
        return None

    for item in ASSUNTOS_MANIFESTACAO:
        if str(item["id"]) == valor_norm or item["titulo"].lower() == valor_norm:
            return item["id"]

    return None

def _resolver_tipo_id(valor: str) -> Optional[int]:
    """Resolve um valor (id ou título) para o id interno do tipo."""
    valor_norm = valor.strip().lower()
    if not valor_norm:
        return None

    for item in TIPOS_MANIFESTACAO:
        # compara tanto pelo id quanto pelo título
        if str(item["id"]) == valor_norm or item["titulo"].lower() == valor_norm:
            return item["id"]

    return None


def _resolver_tipo_doc(valor: str) -> Optional[str]:
    valor_lower = valor.strip().lower()
    if valor_lower in TIPOS_DOCUMENTO:
        return TIPOS_DOCUMENTO[valor_lower]["valor"]

    mapa = {
        "cpf": "CPF",
        "cnpj": "CNPJ",
        "rg": "RG",
        "registro_profissional": "Registro Profissional",
        "cnh": "CNH",
        "outro": "Outro",
    }

    for chave, doc_val in mapa.items():
        if chave in valor_lower:
            return doc_val

    return None


# --- Custom ASK actions ---

class ActionAskTipoManifestacao(Action):
    def name(self) -> Text:
        return "action_ask_tipo_manifestacao"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Dict[Text, Any]]:
        events = []
        dispatcher.utter_message(
            json_message={
                "opcoes": TIPOS_MANIFESTACAO,
                "mensagem": "Qual o tipo de manifestação?",
                "tipo_msn": "interactive"
            }
        )
        return events


class ActionAskAssuntoManifestacao(Action):
    def name(self) -> Text:
        return "action_ask_assunto_manifestacao"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(
            json_message={
                "opcoes": ASSUNTOS_MANIFESTACAO,
                "mensagem": "Qual o assunto da manifestação?",
                "tipo_msn": "interactive"
            },
        )
        return []


class ActionAskMensagemManifestacao(Action):
    def name(self) -> Text:
        return "action_ask_mensagem_manifestacao"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(text="Descreva sua manifestação (mínimo 10 caracteres):")
        return []


class ActionAskQuerAnexo(Action):
    def name(self) -> Text:
        return "action_ask_quer_anexo"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(
            json_message={
                "opcoes": [{"id": 1, "titulo": "Sim"}, {"id": 2, "titulo": "Não"}],
                "mensagem": "Deseja anexar arquivo(s) a esta manifestação?",
                "tipo_msn": "interactive-reply"
            }
        )
        return []


class ActionAskAnexos(Action):
    def name(self) -> Text:
        return "action_ask_anexos"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Dict[Text, Any]]:
        lista = tracker.get_slot("lista_anexos") or []
        total = len(lista)
        if total > 0:
            dispatcher.utter_message(
                text=f"{total} arquivo(s) recebido(s).\n\nEnvie mais arquivos ou digite *pronto* para continuar."
            )
        else:
            dispatcher.utter_message(
                text="Envie o arquivo (imagem, documento, etc.).\nVocê pode enviar vários, um de cada vez.\n\nQuando terminar, digite *pronto*."
            )
        return []


class ActionAskSigilo(Action):
    def name(self) -> Text:
        return "action_ask_sigilo"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(
            json_message={
                "opcoes": [{"id": 1, "titulo": "Sim"}, {"id": 2, "titulo": "Não"}],
                "mensagem": "Deseja preservar sua identidade (sigilo)?",
                "tipo_msn": "interactive-reply"
            }
        )
        return []


class ActionAskTipoDocumento(Action):
    def name(self) -> Text:
        return "action_ask_tipo_documento"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(
            json_message={
                "opcoes": TIPOS_DOCUMENTO,
                "mensagem": "Qual o tipo de documento?",
                "tipo_msn": "interactive"
            }
        )
        return []


class ActionAskNumeroDocumento(Action):
    def name(self) -> Text:
        return "action_ask_numero_documento"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(text="Informe o numero do documento:")
        return []


class ActionAskConfirmaAnonimo(Action):
    def name(self) -> Text:
        return "action_ask_confirma_anonimo"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(
            text="Ao enviar como anonimo, você não precisara se identificar.\nConfirma o envio anonimo?\n\n1 - Sim\n2 - Não"
        )
        return []


class ActionAskConfirmaDados(Action):
    def name(self) -> Text:
        return "action_ask_confirma_dados"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Dict[Text, Any]]:
        dados = tracker.get_slot("dados_pessoa") or {}
        nome = dados.get("nome", "N/A")
        email = dados.get("email", "N/A")

        dispatcher.utter_message(
            text=f"Encontramos seu cadastro:\n\nNome: {nome}\nE-mail: {email}\n\nOs dados estão corretos?\n\n1 - Sim\n2 - Não"
        )
        return []


class ActionAskNomeCompleto(Action):
    def name(self) -> Text:
        return "action_ask_nome_completo"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(text="Informe seu nome completo:")
        return []


class ActionAskEmail(Action):
    def name(self) -> Text:
        return "action_ask_email"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(text="Informe seu e-mail:")
        return []


class ActionAskTelefone(Action):
    def name(self) -> Text:
        return "action_ask_telefone"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(text="Informe seu telefone:")
        return []


class ActionAskConfirmaEnvio(Action):
    def name(self) -> Text:
        return "action_ask_confirma_envio"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Dict[Text, Any]]:
        # Recupera o id do tipo a partir do valor armazenado no slot
        tipo_raw = tracker.get_slot("tipo_manifestacao") or ""
        tipo_id = _resolver_tipo_id(str(tipo_raw))

        tipo_nome = str(tipo_raw)
        if tipo_id is not None:
            for item in TIPOS_MANIFESTACAO:
                if item["id"] == tipo_id:
                    tipo_nome = item["titulo"]
                    break

        # Recupera o id do assunto a partir do valor armazenado no slot
        assunto_raw = tracker.get_slot("assunto_manifestacao") or ""
        assunto_id = _resolver_assunto_id(str(assunto_raw))

        assunto_nome = str(assunto_raw)
        if assunto_id is not None:
            for item in ASSUNTOS_MANIFESTACAO:
                if item["id"] == assunto_id:
                    assunto_nome = item["titulo"]
                    break

        mensagem = tracker.get_slot("mensagem_manifestacao") or ""
        resumo_msg = mensagem[:80] + "..." if len(mensagem) > 80 else mensagem

        lista_anexos = tracker.get_slot("lista_anexos") or []
        total_anexos = len(lista_anexos)
        anexos_txt = f"*Anexos*: {total_anexos} arquivo(s)" if total_anexos > 0 else "*Anexos*: nenhum(s)"

        eh_sigilo = tracker.get_slot("sigilo") == "1"
        nome = tracker.get_slot("nome_completo") or ""
        email = tracker.get_slot("email") or ""
        telefone = tracker.get_slot("telefone") or ""
        numero_documento = tracker.get_slot("numero_documento") or ""

        texto_usuario = (
            f"*Nome*: {nome}\n" +
            f"*E-mail*: {email}\n" +
            f"*Telefone*: {telefone}\n" +
            f"*Número do documento*: {numero_documento}\n"
        )
        
        if eh_sigilo:
            texto = (
            f"*Resumo da manifestação*:\n\n"
            f"*Tipo*: {tipo_nome}\n"
            f"*Assunto*: {assunto_nome}\n"    
            f"*Mensagem*: {resumo_msg}\n"
            f"{anexos_txt}\n\n"
        )
        else:
            texto = (
            f"*Resumo da manifestação*:\n\n"
            f"*Tipo*: {tipo_nome}\n"
            f"*Assunto*: {assunto_nome}\n"    
            f"*Mensagem*: {resumo_msg}\n\n"
            f"{texto_usuario}\n"
            f"{anexos_txt}\n\n"
        )
        
        dispatcher.utter_message(text=texto)
        dispatcher.utter_message(
            json_message={
                "opcoes": [{"id": 1, "titulo": "Sim"}, {"id": 2, "titulo": "Não"}],
                "mensagem": "Confirma o envio da manifestação?",
                "tipo_msn": "interactive-reply"
            }
        )
        return []


# --- Form Validation ---

class ValidateManifestacaoForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_manifestacao_form"

    async def required_slots(
        self,
        domain_slots: List[Text],
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> List[Text]:
        slots = [
            "tipo_manifestacao",
            "assunto_manifestacao",
            "mensagem_manifestacao",
            "quer_anexo",
        ]

        quer_anexo = tracker.get_slot("quer_anexo")
        if quer_anexo == "1":
            slots.append("anexos")

        slots.append("sigilo")

        sigilo = tracker.get_slot("sigilo")

        if sigilo == "1":
            slots.append("confirma_envio")
            return slots

        slots.append("tipo_documento")

        tipo_doc = tracker.get_slot("tipo_documento")

        if tipo_doc:
            doc_resolvido = _resolver_tipo_doc(tipo_doc)
            if doc_resolvido == "anonimo":
                slots.append("confirma_anonimo")
            else:
                slots.append("numero_documento")

                pessoa_encontrada = tracker.get_slot("pessoa_encontrada")
                if pessoa_encontrada is True:
                    slots.append("confirma_dados")
                elif pessoa_encontrada is False:
                    slots.extend(["nome_completo", "email", "telefone"])

        slots.append("confirma_envio")
        return slots

    def validate_tipo_manifestacao(
        self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        valor = str(slot_value).strip()
        if not valor:
            return {"tipo_manifestacao": None}

        # Tenta resolver para um id válido (aceita tanto "1" quanto "Denúncia")
        tipo_id = _resolver_tipo_id(valor)
        if tipo_id is not None:
            logger.info(f"TIPO ENCONTRADO: valor='{valor}' -> id={tipo_id}")
            # guarda o id como string no slot
            return {"tipo_manifestacao": str(tipo_id)}

        dispatcher.utter_message(text="Opção inválida. Escolha uma das opções abaixo:" )
        return {"tipo_manifestacao": None}

    def validate_assunto_manifestacao(
        self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        valor = str(slot_value).strip()
        if not valor:
            return {"assunto_manifestacao": None}

        assunto_id = _resolver_assunto_id(valor)
        if assunto_id is not None:
            logger.warning(f"ASSUNTO ENCONTRADO: valor='{valor}' -> id={assunto_id}")
            # guarda sempre o id em formato string
            return {"assunto_manifestacao": str(assunto_id)}

        dispatcher.utter_message(text="Opção inválida. Escolha uma das opções abaixo:" )
        return {"assunto_manifestacao": None}

    def validate_mensagem_manifestacao(
        self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        if slot_value and len(str(slot_value).strip()) >= 10:
            return {"mensagem_manifestacao": str(slot_value)}

        dispatcher.utter_message(text="A mensagem deve ter no mínimo 10 caracteres. Tente novamente.")
        return {"mensagem_manifestacao": None}

    def validate_quer_anexo(
        self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        valor = str(slot_value).strip().lower()
        if valor in ("1", "sim", "s"):
            return {"quer_anexo": "1", "lista_anexos": []}
        if valor in ("2", "não", "n"):
            return {"quer_anexo": "0", "anexos": "sem_anexo", "lista_anexos": []}

        dispatcher.utter_message(text="Opção inválida. Digite 1 para Sim ou 2 para Não.")
        return {"quer_anexo": None}

    def validate_anexos(
        self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        lista = tracker.get_slot("lista_anexos") or []

        midia = _extrair_midia_whatsapp(tracker)
        if midia:
            lista.append(midia)
            total = len(lista)
            dispatcher.utter_message(
                text=f"Arquivo recebido! ({total} no total)\n\nEnvie mais arquivos ou digite *pronto* para continuar."
            )
            return {"anexos": None, "lista_anexos": lista}

        valor = str(slot_value).strip().lower()
        if valor in ("pronto", "ok", "finalizar", "continuar", "2", "não", "n"):
            total = len(lista)
            if total > 0:
                dispatcher.utter_message(text=f"{total} arquivo(s) anexado(s).")
            else:
                dispatcher.utter_message(text="Nenhum arquivo anexado(s).")
            return {"anexos": "concluido", "lista_anexos": lista}

        dispatcher.utter_message(
            text="Envie um arquivo ou digite *pronto* para continuar sem mais anexos."
        )
        return {"anexos": None, "lista_anexos": lista}

    def validate_sigilo(
        self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        valor = str(slot_value).strip().lower()
        if valor in ("1", "sim", "s", "quero"):
            return {"sigilo": "1"}
        if valor in ("2", "não", "n", "não quero"):
            return {"sigilo": "0"}

        dispatcher.utter_message(text="Opção inválida. Digite 1 para Sim ou 2 para Não.")
        return {"sigilo": None}

    def validate_tipo_documento(
        self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        doc = _resolver_tipo_doc(str(slot_value))
        if doc:
            eh_anonimo = doc == "anonimo"
            return {"tipo_documento": str(slot_value), "eh_anonimo": eh_anonimo}

        dispatcher.utter_message(text="Opção inválida. Escolha um número de 1 a 6.")
        return {"tipo_documento": None}

    def validate_numero_documento(
        self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        valor_bruto = str(slot_value).strip()
        numero = re.sub(r"[^0-9a-zA-Z]", "", valor_bruto)

        # Descobre tipo de documento resolvido (CPF, CNPJ, RG, CNH, Outro)
        tipo_doc_raw = tracker.get_slot("tipo_documento") or ""
        tipo_doc = _resolver_tipo_doc(str(tipo_doc_raw) or "")

        # Validação por tipo
        if tipo_doc == "CPF":
            if not (len(numero) == 11 and numero.isdigit()):
                dispatcher.utter_message(text="CPF inválido. Informe 11 dígitos (apenas números).")
                return {"numero_documento": None}

        elif tipo_doc == "CNPJ":
            if not (len(numero) == 14 and numero.isdigit()):
                dispatcher.utter_message(text="CNPJ inválido. Informe 14 dígitos (apenas números).")
                return {"numero_documento": None}

        elif tipo_doc == "RG":
            # RG muito curto é estranho; aceita letras e números
            if len(numero) < 5:
                dispatcher.utter_message(text="RG inválido. Informe um número de RG válido.")
                return {"numero_documento": None}

        elif tipo_doc == "CNH":
            if not (len(numero) == 11 and numero.isdigit()):
                dispatcher.utter_message(text="CNH inválida. Informe 11 dígitos (apenas números).")
                return {"numero_documento": None}

        else:
            # Tipo "Outro" ou não identificado: validação mínima
            if len(numero) < 3:
                dispatcher.utter_message(text="Número de documento inválido. Tente novamente.")
                return {"numero_documento": None}

        return {
            "numero_documento": valor_bruto,
            "pessoa_encontrada": False,
            "dados_pessoa": None,
            "pessoa_id": None,
        }

    def validate_confirma_anonimo(
        self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        valor = str(slot_value).strip().lower()
        if valor in ("1", "sim", "s"):
            return {"confirma_anonimo": "sim"}
        if valor in ("2", "nao", "n"):
            dispatcher.utter_message(text="Certo. Escolha outro tipo de documento.")
            return {
                "confirma_anonimo": None,
                "tipo_documento": None,
                "eh_anonimo": None,
            }

        dispatcher.utter_message(text="Opcao invalida. Digite 1 para Sim ou 2 para Nao.")
        return {"confirma_anonimo": None}

    def validate_confirma_dados(
        self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        valor = str(slot_value).strip().lower()
        if valor in ("1", "sim", "s"):
            return {"confirma_dados": "sim"}
        if valor in ("2", "nao", "n"):
            return {
                "confirma_dados": None,
                "pessoa_encontrada": False,
                "dados_pessoa": None,
                "pessoa_id": None,
            }

        dispatcher.utter_message(text="Opção inválida. Digite 1 para Sim ou 2 para Não.")
        return {"confirma_dados": None}

    def validate_nome_completo(
        self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        if slot_value and len(str(slot_value).strip()) >= 3:
            return {"nome_completo": str(slot_value).strip()}

        dispatcher.utter_message(text="Nome inválido. Informe seu nome completo.")
        return {"nome_completo": None}

    def validate_email(
        self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if slot_value and re.match(email_regex, str(slot_value).strip()):
            return {"email": str(slot_value).strip()}

        dispatcher.utter_message(text="E-mail inválido. Informe um e-mail válido (ex: nome@email.com).")
        return {"email": None}

    def validate_telefone(
        self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        telefone = re.sub(r"[^0-9]", "", str(slot_value).strip())
        if len(telefone) >= 10:
            return {"telefone": telefone}

        dispatcher.utter_message(text="Telefone inválido. Informe com DDD (ex: 62999999999).")
        return {"telefone": None}

    def validate_confirma_envio(
        self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        valor = str(slot_value).strip().lower()
        if valor in ("Sim", "sim", "S"):
            return {"confirma_envio": "sim"}
        if valor in ("Não", "não", "N"):
            return {"confirma_envio": "cancelar"}

        dispatcher.utter_message(text="Opção inválida. Selecione Sim ou Não.")
        return {"confirma_envio": None}


# --- Action: Enviar Manifestação ---

class ActionEnviarManifestacao(Action):
    def name(self) -> Text:
        return "action_enviar_manifestacao"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> List[Dict[Text, Any]]:
        confirma = tracker.get_slot("confirma_envio")
        if confirma == "cancelar":
            dispatcher.utter_message(
                text=f"Manifestação cancelada."
            )
        else:
            dispatcher.utter_message(
                text=f"Manifestação registrada com sucesso!\nObrigado por utilizar a Ouvidoria."
            )

        dispatcher.utter_message(
            json_message={
                "opcoes": MENU_OPCOES_2,
                "mensagem": "O que deseja fazer agora?",
                "tipo_msn": "interactive-reply"
            }
        )

        return [
            SlotSet("tipo_manifestacao", None),
            SlotSet("assunto_manifestacao", None),
            SlotSet("mensagem_manifestacao", None),
            SlotSet("quer_anexo", None),
            SlotSet("anexos", None),
            SlotSet("lista_anexos", None),
            SlotSet("sigilo", None),
            SlotSet("tipo_documento", None),
            SlotSet("numero_documento", None),
            SlotSet("confirma_anonimo", None),
            SlotSet("confirma_dados", None),
            SlotSet("nome_completo", None),
            SlotSet("email", None),
            SlotSet("telefone", None),
            SlotSet("confirma_envio", None),
            SlotSet("eh_anonimo", None),
            SlotSet("pessoa_encontrada", None),
            SlotSet("dados_pessoa", None),
            SlotSet("pessoa_id", None),
            SlotSet("codigo_acesso", None),
            SlotSet("lista_tipos", None),
            SlotSet("lista_assuntos", None),
        ]

