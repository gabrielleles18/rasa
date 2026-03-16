# 8. Como Treinar o Bot

Comando básico (dentro do container Docker):

```bash
# Treinar o modelo completo (NLU + Core)
docker compose run --rm rasa train

# Treinar só o NLU (mais rápido, se só mudou nlu.yml)
docker compose run --rm rasa train nlu

# Treinar só o Core (se só mudou stories/rules)
docker compose run --rm rasa train core
```

### Opções do `rasa train`

| Flag | Função | Exemplo |
|------|--------|---------|
| `--domain` | Caminho do domain | `--domain domain.yml` |
| `--data` | Caminho dos dados | `--data data/` |
| `--config` | Caminho do config | `--config config.yml` |
| `--out` | Pasta de saída do modelo | `--out models/` |
| `--fixed-model-name` | Nome fixo para o modelo | `--fixed-model-name ouvidoria` |
| `--augmentation` | Fator de augmentação das stories | `--augmentation 50` (padrão 50) |
| `--num-threads` | Threads para treino | `--num-threads 4` |
| `--epoch-fraction` | Fração dos epochs (para teste rápido) | `--epoch-fraction 0.5` (metade) |
| `--force` | Força retreino mesmo sem mudanças | `--force` |

### Exemplo de treino com opções

```bash
docker compose run --rm rasa train \
  --fixed-model-name ouvidoria \
  --augmentation 50 \
  --num-threads 4
```

### Depois de treinar, subir o bot

```bash
# Subir em background
docker compose up -d

# Ou subir e ver os logs
docker compose up
```

### Testar o bot

```bash
# Testar no shell interativo
docker compose run --rm rasa shell

# Testar via API REST (o bot já está rodando na porta 5005)
curl -X POST http://localhost:5005/webhooks/rest/webhook \
  -H "Content-Type: application/json" \
  -d '{"sender": "test", "message": "oi"}'

# Validar os dados de treino (sem treinar)
docker compose run --rm rasa data validate

# Ver o NLU em ação (testar classificação de intents)
docker compose run --rm rasa test nlu
```

---

# 9. Fluxo de Trabalho Recomendado

1. **Editar os YMLs** (nlu, stories, rules, domain)
2. **Validar** → `docker compose run --rm rasa data validate`
3. **Treinar** → `docker compose run --rm rasa train`
4. **Testar** → `docker compose run --rm rasa shell` ou via API
5. **Iterar** → Adicionar mais exemplos de NLU, mais stories, ajustar thresholds

### Dicas de tuning

- Se o bot **confunde intents** → adicione mais exemplos no `nlu.yml`, aumente epochs do `DIETClassifier`
- Se o bot **não entende nada** → abaixe o threshold do `FallbackClassifier` (ex: `0.2`)
- Se o bot **responde coisas aleatórias** → aumente o threshold (ex: `0.5`)
- `ambiguity_threshold: 0.1` significa que se as 2 intents mais prováveis têm diferença menor que 10%, dispara fallback
- `max_history` no `TEDPolicy` controla quantos turnos de conversa ele considera para decidir a próxima ação
