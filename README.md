# README - Sistema de Orquestração de Agentes

## Visão Geral

Este projeto implementa uma aplicação completa de orquestração de agentes de IA usando o Semantic Kernel da Microsoft em Python. O sistema permite criar e coordenar agentes especializados para resolver tarefas complexas através de diferentes padrões de orquestração.

## Características Principais

- **4 Agentes Especializados**: Analista, Redator, Planejador e Revisor
- **4 Padrões de Orquestração**: Sequencial, Concorrente, Chat em Grupo e Handoff
- **Interface Web Intuitiva**: Gerenciamento completo via navegador
- **Sistema de Métricas**: Monitoramento de performance e uso
- **Arquitetura Modular**: Fácil extensão e personalização

## Estrutura do Projeto

```
agent_orchestrator/
├── orchestrator_base.py      # Classes base do orquestrador
├── specialized_agents.py     # Agentes especializados
├── orchestration_system.py   # Sistema principal
├── config_utils.py          # Configurações e utilitários
├── web_interface.py         # Interface web Flask
├── test_system.py           # Testes automatizados
├── demo_system.py           # Demonstração sem API
└── documentacao_completa.md # Documentação técnica
```

## Instalação e Configuração

### 1. Criar Ambiente Virtual

```bash
python3.11 -m venv sk_env
source sk_env/bin/activate  # Linux/Mac
# ou
sk_env\Scripts\activate     # Windows
```

### 2. Instalar Dependências

```bash
pip install semantic-kernel flask flask-cors
```

### 3. Configurar Chave API

```bash
set OPENAI_API_KEY="sua_chave_aqui"
```

### 4. Executar Testes

```bash
cd agent_orchestrator
python test_system.py
```

### 5. Iniciar Interface Web

```bash
python web_interface.py
```

A interface estará disponível em `http://localhost:5000`

## Uso Básico

### Criando um Orquestrador

```python
from orchestration_system import OrchestrationSystem

# Inicializar sistema
system = OrchestrationSystem()
await system.initialize()

# Criar orquestrador sequencial
orchestrator_name = await system.create_orchestrator(
    name="meu_orquestrador",
    pattern="sequential",
    agent_names=["Analista", "Redator"]
)
```

### Executando uma Tarefa

```python
# Executar orquestração
result = await system.execute_orchestration(
    orchestrator_name="meu_orquestrador",
    task="Analise o mercado de IA e crie um relatório",
    context={"formato": "executivo"}
)

print(result["final_output"])
```

## Padrões de Orquestração

### Sequencial
Agentes processam em ordem, passando resultados entre si.

### Concorrente
Agentes processam a mesma tarefa em paralelo.

### Chat em Grupo
Agentes colaboram em uma conversa coordenada.

### Handoff
Transferência dinâmica de controle entre agentes.

## Agentes Especializados

### Analista
- Análise de dados e padrões
- Geração de insights
- Interpretação de métricas

### Redator
- Criação de conteúdo
- Adaptação de tom e estilo
- Estruturação de documentos

### Planejador
- Planejamento estratégico
- Organização de tarefas
- Definição de cronogramas

### Revisor
- Controle de qualidade
- Validação de informações
- Sugestões de melhorias

## Demonstração sem API

Para testar sem chave API:

```bash
python demo_system.py
```

## Arquivos de Configuração

O sistema cria automaticamente um `config.json` com configurações padrão:

```json
{
  "llm": {
    "provider": "openai",
    "model_name": "gpt-3.5-turbo",
    "temperature": 0.7
  },
  "orchestration": {
    "max_iterations": 10,
    "timeout": 300
  }
}
```

## Métricas e Monitoramento

O sistema coleta automaticamente:
- Número de orquestrações executadas
- Taxa de sucesso/falha
- Tempo médio de execução
- Uso por agente e padrão

## Extensibilidade

### Criando Novos Agentes

```python
class MeuAgente(SemanticKernelAgent):
    def __init__(self, llm_config):
        config = AgentConfig(
            name="MeuAgente",
            description="Descrição do agente",
            capabilities=["capacidade1", "capacidade2"],
            model_config={"provider": "openai"}
        )
        super().__init__(config, llm_config)
```

### Adicionando Novos Padrões

Estenda a classe `AgentOrchestrator` e implemente novos métodos de orquestração.

## Troubleshooting

### Erro de Chave API
Verifique se `OPENAI_API_KEY` está configurada corretamente.

### Erro de Dependências
Reinstale as dependências:
```bash
pip install --upgrade semantic-kernel flask flask-cors
```

### Problemas de Rede
Verifique conectividade com a API da OpenAI.

## Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## Licença

Este projeto é fornecido como exemplo educacional e de demonstração.

## Suporte

Para dúvidas e suporte, consulte a documentação completa em `documentacao_completa.md`.

---

**Desenvolvido com Semantic Kernel e Python**

