# Rasa Pro - Guia de Integração

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) instalado
- [Docker Compose](https://docs.docker.com/compose/install/) instalado
- Chave de licença do Rasa Pro (`RASA_LICENSE`)

## Configuração Inicial

### 1. Criar o arquivo `.env`

Crie um arquivo `.env` na raiz do projeto com sua chave de licença:

```
RASA_LICENSE=sua-chave-de-licenca-aqui
```

### 2. Subir o container

```bash
docker compose up --build
```

O Rasa ficará disponível em `http://localhost:5005`.

## Estrutura do Projeto

```
rasa/
├── .env                 # Variáveis de ambiente (não commitar)
├── Dockerfile           # Imagem customizada do Rasa Pro
├── docker-compose.yml   # Orquestração dos serviços
├── config.yml           # Configuração do pipeline NLU e políticas
├── domain.yml           # Domínio (intents, entities, responses, actions)
├── credentials.yml      # Credenciais dos canais de comunicação
├── endpoints.yml        # Endpoints externos (action server, tracker store)
├── connectors/
│   └── whatsapp.py      # Conector customizado para WhatsApp Cloud API
└── data/
    ├── nlu.yml          # Dados de treino para NLU
    ├── stories.yml      # Histórias de conversação
    └── rules.yml        # Regras de conversação
```

## Comandos Úteis

Todos os comandos são executados via Docker Compose.

### Inicializar projeto (gerar arquivos base)

```bash
docker compose run --rm rasa init --no-prompt
```

### Treinar o modelo

```bash
docker compose run --rm rasa train
```

### Iniciar o servidor

```bash
docker compose up
```

### Testar no terminal (modo shell)

```bash
docker compose run --rm rasa shell
```

### Validar os dados de treino

```bash
docker compose run --rm rasa data validate
```

### Testar as stories

```bash
docker compose run --rm rasa test
```

## Interagindo com o Rasa

### Via API REST

Com o servidor rodando (`docker compose up`), envie mensagens via HTTP:

```bash
curl -X POST http://localhost:5005/webhooks/rest/webhook \
  -H "Content-Type: application/json" \
  -d '{"sender": "usuario1", "message": "oi"}'
```

A resposta será um JSON com as mensagens do bot:

```json
[{"recipient_id": "usuario1", "text": "Olá! Como posso ajudar?"}]
```

### Via Terminal

```bash
docker compose run --rm rasa shell
```

Digite suas mensagens diretamente no terminal para testar o bot.

## Integração com WhatsApp Cloud API (Meta)

Este projeto usa um **conector customizado gratuito** que se conecta diretamente à WhatsApp Cloud API da Meta, sem necessidade de serviços pagos como Twilio.

### 1. Criar um App no Meta Developers

1. Acesse [developers.facebook.com](https://developers.facebook.com/)
2. Crie um novo app do tipo **Business**
3. Adicione o produto **WhatsApp**
4. No painel do WhatsApp, você encontrará:
   - **Phone Number ID** — ID do número de telefone
   - **Temporary Access Token** — Token de acesso (gere um permanente para produção)
5. Em **Configuration > Webhook**, configure:
   - **Callback URL**: `https://seu-dominio.com/webhooks/whatsapp/webhook`
   - **Verify Token**: uma string qualquer que você define (ex: `meu_token_secreto`)
   - Assine o campo **messages**

### 2. Configurar o `.env`

```
RASA_LICENSE=sua-chave-rasa

# WhatsApp Cloud API
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxx
WHATSAPP_VERIFY_TOKEN=meu_token_secreto
WHATSAPP_APP_SECRET=abc123def456
```

### 3. Configurar o `credentials.yml`

```yaml
rest:

connectors.whatsapp.WhatsAppInput:
  phone_number_id: "${WHATSAPP_PHONE_NUMBER_ID}"
  access_token: "${WHATSAPP_ACCESS_TOKEN}"
  verify_token: "${WHATSAPP_VERIFY_TOKEN}"
  app_secret: "${WHATSAPP_APP_SECRET}"
```

### 4. Expor o Rasa para a Internet

O WhatsApp precisa acessar seu webhook. Em desenvolvimento, use o [ngrok](https://ngrok.com/):

```bash
ngrok http 5005
```

Use a URL gerada (ex: `https://abc123.ngrok.io`) como **Callback URL** no Meta Developers:

```
https://abc123.ngrok.io/webhooks/whatsapp/webhook
```

### Custos

| Item | Custo |
|---|---|
| WhatsApp Cloud API | 1.000 conversas/mês grátis |
| Acima de 1.000 | ~R$0,25 por conversa (varia por país) |
| Conector customizado | Grátis (incluso neste projeto) |

## Outros Canais

Edite o `credentials.yml` para conectar a outros canais:

```yaml
# Telegram
telegram:
  access_token: "TOKEN_DO_BOT"
  verify: "NOME_DO_BOT"
  webhook_url: "https://seu-dominio.com/webhooks/telegram/webhook"

# Slack
slack:
  slack_token: "xoxb-SEU-TOKEN"
  slack_signing_secret: "SEU_SIGNING_SECRET"
  slack_channel: "SEU_CANAL"
```

## Configuração do Pipeline NLU

Edite o `config.yml` para definir o pipeline de processamento:

```yaml
language: pt

pipeline:
  - name: WhitespaceTokenizer
  - name: RegexFeaturizer
  - name: LexicalSyntacticFeaturizer
  - name: CountVectorsFeaturizer
  - name: CountVectorsFeaturizer
    analyzer: char_wb
    min_ngram: 1
    max_ngram: 4
  - name: DIETClassifier
    epochs: 100
  - name: EntitySynonymMapper
  - name: ResponseSelector
    epochs: 100

policies:
  - name: MemoizationPolicy
  - name: TEDPolicy
    max_history: 5
    epochs: 100
  - name: RulePolicy
```

## Versão da Imagem

A versão atual configurada no `Dockerfile` é `3.10.6`. Para alterar, edite a primeira linha do `Dockerfile`:

```dockerfile
FROM rasa/rasa-pro:VERSAO_DESEJADA
```

Consulte o [Changelog do Rasa Pro](https://rasa.com/docs/rasa-pro/changelog) para ver as versões disponíveis.

## Solução de Problemas

| Problema | Solução |
|---|---|
| `No space left on device` | Libere espaço em disco: `docker system prune -a` |
| `DNS timeout` ao fazer build | Configure DNS no Docker: adicione `{"dns": ["8.8.8.8"]}` em `/etc/docker/daemon.json` e reinicie com `sudo systemctl restart docker` |
| `RASA_LICENSE` inválida | Verifique se o `.env` contém a chave correta |
| Erro ao baixar TensorFlow (~586MB) | Sua conexão pode estar lenta; tente novamente ou use uma rede mais estável |




# Retreinar o modelo com as alterações
docker exec -it rasa-rasa-1 rasa train

# Subir o action-server (que não está rodando)
docker compose up -d --build action-server

# Reiniciar o rasa para carregar o novo modelo
docker compose restart rasa