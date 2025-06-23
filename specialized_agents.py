"""
Agentes especializados usando Semantic Kernel
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.prompt_template import InputVariable, PromptTemplateConfig
from semantic_kernel.functions import KernelArguments

from orchestrator_base import BaseAgent, AgentConfig
from config_utils import ConfigManager, LLMConfig

logger = logging.getLogger(__name__)


class SemanticKernelAgent(BaseAgent):
    """Agente base usando Semantic Kernel"""
    
    def __init__(self, config: AgentConfig, llm_config: LLMConfig):
        super().__init__(config)
        self.llm_config = llm_config
        self.kernel = None
        self.chat_function = None
        
    async def initialize(self):
        """Inicializa o agente com Semantic Kernel"""
        try:
            # Cria o kernel
            self.kernel = Kernel()
            
            # Configura o serviço de chat
            if self.llm_config.provider == "openai":
                chat_service = OpenAIChatCompletion(
                    ai_model_id=self.llm_config.model_name,
                    api_key=self.llm_config.api_key,
                )
                self.kernel.add_service(chat_service)
            
            # Cria a função de chat personalizada para este agente
            await self._create_chat_function()
            
            logger.info(f"Agente {self.name} inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar agente {self.name}: {str(e)}")
            raise
    
    async def _create_chat_function(self):
        """Cria função de chat personalizada para o agente"""
        prompt_template = f"""
Você é {self.name}, um agente especializado com as seguintes características:

Descrição: {self.description}
Capacidades: {', '.join(self.capabilities)}

Sua tarefa é processar a seguinte entrada e fornecer uma resposta útil e relevante baseada em suas capacidades especializadas.

Entrada: {{{{$input}}}}

Contexto adicional (se fornecido): {{{{$context}}}}

Resposta:
"""
        
        # Configura o template do prompt
        prompt_config = PromptTemplateConfig(
            template=prompt_template,
            name=f"{self.name}_chat",
            description=f"Função de chat para o agente {self.name}",
            input_variables=[
                InputVariable(name="input", description="Entrada do usuário"),
                InputVariable(name="context", description="Contexto adicional", is_required=False)
            ]
        )
        
        # Cria a função no kernel
        self.chat_function = self.kernel.add_function(
            plugin_name="chat",
            function_name=f"{self.name}_process",
            prompt_template_config=prompt_config
        )
    
    async def process(self, input_data: str, context: Dict[str, Any] = None) -> str:
        """Processa entrada usando Semantic Kernel"""
        try:
            # Prepara argumentos
            arguments = KernelArguments(input=input_data)
            
            if context:
                # Converte contexto para string se necessário
                context_str = str(context) if not isinstance(context, str) else context
                arguments["context"] = context_str
            
            # Executa a função
            result = await self.kernel.invoke(self.chat_function, arguments)
            
            return str(result)
            
        except Exception as e:
            logger.error(f"Erro ao processar entrada no agente {self.name}: {str(e)}")
            return f"Erro: {str(e)}"


class AnalystAgent(SemanticKernelAgent):
    """Agente especializado em análise de dados e informações"""
    
    def __init__(self, llm_config: LLMConfig):
        config = AgentConfig(
            name="Analista",
            description="Especialista em análise de dados, identificação de padrões e geração de insights",
            capabilities=[
                "análise de dados",
                "identificação de padrões",
                "geração de relatórios",
                "interpretação de métricas",
                "análise estatística"
            ],
            model_config={
                "provider": llm_config.provider,
                "model_name": llm_config.model_name,
                "temperature": llm_config.temperature
            }
        )
        super().__init__(config, llm_config)
    
    async def _create_chat_function(self):
        """Cria função de chat especializada para análise"""
        prompt_template = """
Você é um Agente Analista especializado em análise de dados e geração de insights.

Suas capacidades incluem:
- Análise de dados quantitativos e qualitativos
- Identificação de padrões e tendências
- Geração de relatórios estruturados
- Interpretação de métricas e KPIs
- Análise estatística básica

Quando receber dados ou informações para analisar:
1. Identifique os principais pontos e padrões
2. Forneça insights relevantes
3. Sugira ações baseadas na análise
4. Estruture sua resposta de forma clara e objetiva

Entrada para análise: {{$input}}

Contexto adicional: {{$context}}

Análise:
"""
        
        prompt_config = PromptTemplateConfig(
            template=prompt_template,
            name="analyst_chat",
            description="Função de análise especializada",
            input_variables=[
                InputVariable(name="input", description="Dados para análise"),
                InputVariable(name="context", description="Contexto adicional", is_required=False)
            ]
        )
        
        self.chat_function = self.kernel.add_function(
            plugin_name="analyst",
            function_name="analyze",
            prompt_template_config=prompt_config
        )


class WriterAgent(SemanticKernelAgent):
    """Agente especializado em criação de conteúdo e redação"""
    
    def __init__(self, llm_config: LLMConfig):
        config = AgentConfig(
            name="Redator",
            description="Especialista em criação de conteúdo, redação e comunicação",
            capabilities=[
                "redação de textos",
                "criação de conteúdo",
                "edição e revisão",
                "adaptação de tom e estilo",
                "estruturação de documentos"
            ],
            model_config={
                "provider": llm_config.provider,
                "model_name": llm_config.model_name,
                "temperature": llm_config.temperature
            }
        )
        super().__init__(config, llm_config)
    
    async def _create_chat_function(self):
        """Cria função de chat especializada para redação"""
        prompt_template = """
Você é um Agente Redator especializado em criação de conteúdo e comunicação.

Suas capacidades incluem:
- Redação de textos claros e envolventes
- Criação de conteúdo para diferentes públicos
- Edição e revisão de textos
- Adaptação de tom e estilo conforme necessário
- Estruturação de documentos e relatórios

Quando receber uma solicitação de redação:
1. Identifique o público-alvo e objetivo
2. Escolha o tom e estilo apropriados
3. Estruture o conteúdo de forma lógica
4. Use linguagem clara e persuasiva
5. Revise para garantir qualidade

Solicitação: {{$input}}

Contexto e diretrizes: {{$context}}

Conteúdo criado:
"""
        
        prompt_config = PromptTemplateConfig(
            template=prompt_template,
            name="writer_chat",
            description="Função de redação especializada",
            input_variables=[
                InputVariable(name="input", description="Solicitação de redação"),
                InputVariable(name="context", description="Contexto e diretrizes", is_required=False)
            ]
        )
        
        self.chat_function = self.kernel.add_function(
            plugin_name="writer",
            function_name="write",
            prompt_template_config=prompt_config
        )


class PlannerAgent(SemanticKernelAgent):
    """Agente especializado em planejamento e estratégia"""
    
    def __init__(self, llm_config: LLMConfig):
        config = AgentConfig(
            name="Planejador",
            description="Especialista em planejamento estratégico e organização de tarefas",
            capabilities=[
                "planejamento estratégico",
                "organização de tarefas",
                "definição de prioridades",
                "criação de cronogramas",
                "análise de recursos"
            ],
            model_config={
                "provider": llm_config.provider,
                "model_name": llm_config.model_name,
                "temperature": llm_config.temperature
            }
        )
        super().__init__(config, llm_config)
    
    async def _create_chat_function(self):
        """Cria função de chat especializada para planejamento"""
        prompt_template = """
Você é um Agente Planejador especializado em estratégia e organização.

Suas capacidades incluem:
- Planejamento estratégico e tático
- Organização e priorização de tarefas
- Definição de cronogramas e marcos
- Análise de recursos necessários
- Identificação de riscos e dependências

Quando receber uma solicitação de planejamento:
1. Analise os objetivos e requisitos
2. Identifique as principais etapas e marcos
3. Defina prioridades e dependências
4. Estime recursos e tempo necessários
5. Identifique possíveis riscos e mitigações
6. Estruture um plano claro e executável

Solicitação de planejamento: {{$input}}

Contexto e restrições: {{$context}}

Plano estratégico:
"""
        
        prompt_config = PromptTemplateConfig(
            template=prompt_template,
            name="planner_chat",
            description="Função de planejamento especializada",
            input_variables=[
                InputVariable(name="input", description="Solicitação de planejamento"),
                InputVariable(name="context", description="Contexto e restrições", is_required=False)
            ]
        )
        
        self.chat_function = self.kernel.add_function(
            plugin_name="planner",
            function_name="plan",
            prompt_template_config=prompt_config
        )


class ReviewerAgent(SemanticKernelAgent):
    """Agente especializado em revisão e controle de qualidade"""
    
    def __init__(self, llm_config: LLMConfig):
        config = AgentConfig(
            name="Revisor",
            description="Especialista em revisão, controle de qualidade e validação",
            capabilities=[
                "revisão de conteúdo",
                "controle de qualidade",
                "validação de informações",
                "identificação de erros",
                "sugestões de melhorias"
            ],
            model_config={
                "provider": llm_config.provider,
                "model_name": llm_config.model_name,
                "temperature": llm_config.temperature
            }
        )
        super().__init__(config, llm_config)
    
    async def _create_chat_function(self):
        """Cria função de chat especializada para revisão"""
        prompt_template = """
Você é um Agente Revisor especializado em controle de qualidade e validação.

Suas capacidades incluem:
- Revisão detalhada de conteúdo
- Controle de qualidade rigoroso
- Validação de informações e dados
- Identificação de erros e inconsistências
- Sugestões de melhorias e otimizações

Quando receber conteúdo para revisão:
1. Analise a precisão e consistência
2. Verifique a estrutura e organização
3. Identifique erros ou problemas
4. Avalie a qualidade geral
5. Forneça feedback construtivo
6. Sugira melhorias específicas

Conteúdo para revisão: {{$input}}

Critérios e contexto: {{$context}}

Revisão e feedback:
"""
        
        prompt_config = PromptTemplateConfig(
            template=prompt_template,
            name="reviewer_chat",
            description="Função de revisão especializada",
            input_variables=[
                InputVariable(name="input", description="Conteúdo para revisão"),
                InputVariable(name="context", description="Critérios e contexto", is_required=False)
            ]
        )
        
        self.chat_function = self.kernel.add_function(
            plugin_name="reviewer",
            function_name="review",
            prompt_template_config=prompt_config
        )


class AgentFactory:
    """Factory para criação de agentes especializados"""
    
    @staticmethod
    def create_agent(agent_type: str, llm_config: LLMConfig) -> SemanticKernelAgent:
        """Cria um agente do tipo especificado"""
        agents = {
            "analyst": AnalystAgent,
            "writer": WriterAgent,
            "planner": PlannerAgent,
            "reviewer": ReviewerAgent
        }
        
        if agent_type.lower() not in agents:
            raise ValueError(f"Tipo de agente não suportado: {agent_type}")
        
        return agents[agent_type.lower()](llm_config)
    
    @staticmethod
    def get_available_agents() -> List[str]:
        """Retorna lista de agentes disponíveis"""
        return ["analyst", "writer", "planner", "reviewer"]


if __name__ == "__main__":
    # Exemplo de uso
    async def test_agents():
        # Configuração de teste (você precisará de uma chave API válida)
        config_manager = ConfigManager()
        llm_config = config_manager.get_llm_config()
        
        if not llm_config.api_key:
            print("Aviso: Chave API não configurada. Configure OPENAI_API_KEY para testar.")
            return
        
        # Cria agentes
        analyst = AgentFactory.create_agent("analyst", llm_config)
        writer = AgentFactory.create_agent("writer", llm_config)
        
        # Inicializa agentes
        await analyst.initialize()
        await writer.initialize()
        
        print("Agentes especializados criados com sucesso!")
        print(f"Analista: {analyst.description}")
        print(f"Redator: {writer.description}")
    
    # Executa teste se executado diretamente
    print("Agentes especializados implementados:")
    for agent_type in AgentFactory.get_available_agents():
        print(f"- {agent_type}")

