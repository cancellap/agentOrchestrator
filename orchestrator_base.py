"""
Aplicação Orquestradora de Agentes usando Semantic Kernel
Estrutura base do orquestrador
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrchestrationPattern(Enum):
    """Padrões de orquestração suportados"""
    SEQUENTIAL = "sequential"
    CONCURRENT = "concurrent"
    GROUP_CHAT = "group_chat"
    HANDOFF = "handoff"


@dataclass
class AgentConfig:
    """Configuração de um agente"""
    name: str
    description: str
    capabilities: List[str]
    model_config: Dict[str, Any]
    plugins: List[str] = None


@dataclass
class OrchestrationConfig:
    """Configuração da orquestração"""
    pattern: OrchestrationPattern
    agents: List[AgentConfig]
    max_iterations: int = 10
    timeout: int = 300
    custom_settings: Dict[str, Any] = None


class BaseAgent(ABC):
    """Classe base para agentes"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.name = config.name
        self.description = config.description
        self.capabilities = config.capabilities
        
    @abstractmethod
    async def process(self, input_data: str, context: Dict[str, Any] = None) -> str:
        """Processa uma entrada e retorna uma resposta"""
        pass
    
    @abstractmethod
    async def initialize(self):
        """Inicializa o agente"""
        pass


class AgentOrchestrator:
    """Orquestrador principal de agentes"""
    
    def __init__(self, config: OrchestrationConfig):
        self.config = config
        self.agents: Dict[str, BaseAgent] = {}
        self.pattern = config.pattern
        self.max_iterations = config.max_iterations
        self.timeout = config.timeout
        
    async def register_agent(self, agent: BaseAgent):
        """Registra um agente no orquestrador"""
        self.agents[agent.name] = agent
        await agent.initialize()
        logger.info(f"Agente {agent.name} registrado com sucesso")
    
    async def orchestrate(self, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Executa a orquestração baseada no padrão configurado"""
        logger.info(f"Iniciando orquestração com padrão: {self.pattern.value}")
        logger.info(f"Tarefa: {task}")
        
        if context is None:
            context = {}
        
        try:
            if self.pattern == OrchestrationPattern.SEQUENTIAL:
                return await self._sequential_orchestration(task, context)
            elif self.pattern == OrchestrationPattern.CONCURRENT:
                return await self._concurrent_orchestration(task, context)
            elif self.pattern == OrchestrationPattern.GROUP_CHAT:
                return await self._group_chat_orchestration(task, context)
            elif self.pattern == OrchestrationPattern.HANDOFF:
                return await self._handoff_orchestration(task, context)
            else:
                raise ValueError(f"Padrão de orquestração não suportado: {self.pattern}")
                
        except Exception as e:
            logger.error(f"Erro durante a orquestração: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "pattern": self.pattern.value
            }
    
    async def _sequential_orchestration(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Implementa orquestração sequencial"""
        results = []
        current_input = task
        
        for agent_name, agent in self.agents.items():
            logger.info(f"Processando com agente: {agent_name}")
            result = await agent.process(current_input, context)
            results.append({
                "agent": agent_name,
                "input": current_input,
                "output": result
            })
            current_input = result  # O resultado se torna a entrada do próximo agente
            
        return {
            "success": True,
            "pattern": "sequential",
            "results": results,
            "final_output": current_input
        }
    
    async def _concurrent_orchestration(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Implementa orquestração concorrente"""
        logger.info("Executando processamento concorrente")
        
        # Executa todos os agentes em paralelo
        tasks = []
        for agent_name, agent in self.agents.items():
            tasks.append(self._process_with_agent(agent_name, agent, task, context))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Processa os resultados
        processed_results = []
        for i, result in enumerate(results):
            agent_name = list(self.agents.keys())[i]
            if isinstance(result, Exception):
                processed_results.append({
                    "agent": agent_name,
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        return {
            "success": True,
            "pattern": "concurrent",
            "results": processed_results
        }
    
    async def _group_chat_orchestration(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Implementa orquestração de chat em grupo"""
        conversation_history = [{"role": "user", "content": task}]
        iteration = 0
        
        while iteration < self.max_iterations:
            # Seleciona o próximo agente (implementação simples round-robin)
            agent_names = list(self.agents.keys())
            current_agent_name = agent_names[iteration % len(agent_names)]
            current_agent = self.agents[current_agent_name]
            
            # Prepara o contexto com o histórico da conversa
            chat_context = context.copy()
            chat_context["conversation_history"] = conversation_history
            
            # Processa com o agente atual
            response = await current_agent.process(task, chat_context)
            
            conversation_history.append({
                "role": "agent",
                "agent": current_agent_name,
                "content": response
            })
            
            # Verifica se a conversa deve terminar (implementação simples)
            if "finalizado" in response.lower() or "concluído" in response.lower():
                break
                
            iteration += 1
        
        return {
            "success": True,
            "pattern": "group_chat",
            "conversation_history": conversation_history,
            "iterations": iteration + 1
        }
    
    async def _handoff_orchestration(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Implementa orquestração com handoff"""
        current_agent_name = list(self.agents.keys())[0]  # Começa com o primeiro agente
        handoff_chain = []
        iteration = 0
        
        while iteration < self.max_iterations:
            current_agent = self.agents[current_agent_name]
            
            # Adiciona informação sobre handoff no contexto
            handoff_context = context.copy()
            handoff_context["available_agents"] = list(self.agents.keys())
            handoff_context["current_agent"] = current_agent_name
            
            response = await current_agent.process(task, handoff_context)
            
            handoff_chain.append({
                "agent": current_agent_name,
                "response": response,
                "iteration": iteration
            })
            
            # Determina se deve fazer handoff (implementação simples)
            next_agent = self._determine_next_agent(response, current_agent_name)
            
            if next_agent is None or next_agent == current_agent_name:
                break
                
            current_agent_name = next_agent
            iteration += 1
        
        return {
            "success": True,
            "pattern": "handoff",
            "handoff_chain": handoff_chain,
            "final_agent": current_agent_name
        }
    
    async def _process_with_agent(self, agent_name: str, agent: BaseAgent, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Processa uma tarefa com um agente específico"""
        try:
            result = await agent.process(task, context)
            return {
                "agent": agent_name,
                "success": True,
                "output": result
            }
        except Exception as e:
            return {
                "agent": agent_name,
                "success": False,
                "error": str(e)
            }
    
    def _determine_next_agent(self, response: str, current_agent: str) -> Optional[str]:
        """Determina o próximo agente para handoff (implementação simples)"""
        # Implementação básica - pode ser expandida com lógica mais sofisticada
        agent_names = list(self.agents.keys())
        
        # Procura por menções de outros agentes na resposta
        for agent_name in agent_names:
            if agent_name.lower() in response.lower() and agent_name != current_agent:
                return agent_name
        
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna o status atual do orquestrador"""
        return {
            "pattern": self.pattern.value,
            "agents_count": len(self.agents),
            "agents": list(self.agents.keys()),
            "max_iterations": self.max_iterations,
            "timeout": self.timeout
        }


if __name__ == "__main__":
    # Exemplo de uso básico
    print("Estrutura base do Orquestrador de Agentes criada com sucesso!")
    print("Classes principais:")
    print("- AgentOrchestrator: Orquestrador principal")
    print("- BaseAgent: Classe base para agentes")
    print("- OrchestrationPattern: Padrões de orquestração")
    print("- AgentConfig: Configuração de agentes")

