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
        try:
            await agent.initialize()
            logger.info(f"Agente {agent.name} registrado e inicializado com sucesso no orquestrador.")
        except RuntimeError as e: # Captura erros de inicialização do agente
            logger.error(f"Falha ao inicializar o agente {agent.name} durante o registro no orquestrador: {e}", exc_info=True)
            # Remove o agente se a inicialização falhar para evitar problemas posteriores
            del self.agents[agent.name]
            raise RuntimeError(f"Não foi possível registrar o agente {agent.name} devido a erro na sua inicialização: {e}") from e
        except Exception as e:
            logger.error(f"Erro inesperado ao registrar o agente {agent.name}: {e}", exc_info=True)
            if agent.name in self.agents: # Garante que o agente seja removido em caso de outros erros
                 del self.agents[agent.name]
            raise RuntimeError(f"Erro inesperado ao registrar o agente {agent.name}: {e}") from e

    async def orchestrate(self, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Executa a orquestração baseada no padrão configurado"""
        logger.info(f"Iniciando orquestração com padrão: {self.pattern.value} para a tarefa: '{task[:100]}...'")
        
        if not self.agents:
            logger.error("Nenhum agente registrado neste orquestrador. A orquestração não pode prosseguir.")
            return {
                "success": False,
                "error": "Orquestração falhou: Nenhum agente foi registrado no orquestrador.",
                "pattern": self.pattern.value
            }

        if context is None:
            context = {}
        
        try:
            if self.pattern == OrchestrationPattern.SEQUENTIAL:
                result = await self._sequential_orchestration(task, context)
            elif self.pattern == OrchestrationPattern.CONCURRENT:
                result = await self._concurrent_orchestration(task, context)
            elif self.pattern == OrchestrationPattern.GROUP_CHAT:
                result = await self._group_chat_orchestration(task, context)
            elif self.pattern == OrchestrationPattern.HANDOFF:
                result = await self._handoff_orchestration(task, context)
            else:
                # Este caso não deveria acontecer se a validação do padrão for feita na criação.
                logger.error(f"Padrão de orquestração desconhecido ou não suportado: {self.pattern}")
                raise ValueError(f"Padrão de orquestração não suportado: {self.pattern}")

            logger.info(f"Orquestração com padrão {self.pattern.value} concluída.")
            return result
                
        except ValueError as ve: # Erro de valor, como padrão não suportado
            logger.error(f"Erro de valor durante a orquestração: {ve}", exc_info=True)
            return {
                "success": False,
                "error": f"Erro de configuração da orquestração: {ve}",
                "pattern": self.pattern.value
            }
        except RuntimeError as rte: # Erros originados nos agentes ou lógicas internas
            logger.error(f"Erro de execução durante a orquestração: {rte}", exc_info=True)
            return {
                "success": False,
                "error": f"Erro durante a execução da orquestração: {rte}",
                "pattern": self.pattern.value
            }
        except Exception as e: # Captura genérica para erros inesperados
            logger.error(f"Erro inesperado e não tratado durante a orquestração: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Ocorreu um erro inesperado no servidor durante a orquestração: {e}",
                "pattern": self.pattern.value
            }
    
    async def _sequential_orchestration(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Implementa orquestração sequencial"""
        results = []
        current_input = task
        
        for agent_name, agent in self.agents.items():
            try:
                logger.info(f"Padrão Sequencial: Processando com agente: {agent_name}, Input: '{current_input[:50]}...'")
                result = await agent.process(current_input, context)
                results.append({
                    "agent": agent_name,
                    "input": current_input,
                    "output": result,
                    "success": True
                })
                current_input = result  # O resultado se torna a entrada do próximo agente
            except RuntimeError as e:
                logger.error(f"Padrão Sequencial: Erro ao processar com o agente {agent_name}: {e}", exc_info=True)
                results.append({
                    "agent": agent_name,
                    "input": current_input,
                    "output": None,
                    "success": False,
                    "error": f"Agente {agent_name} falhou: {e}"
                })
                # Decide se deve parar ou continuar. Para sequencial, geralmente para.
                # Para robustez, poderia ter uma flag para continuar com o próximo agente se desejado.
                logger.warning(f"Padrão Sequencial: Interrompendo devido à falha do agente {agent_name}.")
                return {
                    "success": False,
                    "pattern": "sequential",
                    "results": results,
                    "final_output": current_input, # Pode ser a última saída bem-sucedida ou o input da falha
                    "error": f"Falha na etapa do agente {agent_name}. Orquestração sequencial interrompida."
                }
            
        return {
            "success": True,
            "pattern": "sequential",
            "results": results,
            "final_output": current_input
        }

    async def _concurrent_orchestration(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Implementa orquestração concorrente"""
        logger.info(f"Padrão Concorrente: Executando processamento para tarefa '{task[:50]}...'")
        
        # Executa todos os agentes em paralelo
        agent_tasks = []
        agent_names_ordered = list(self.agents.keys()) # Mantém a ordem para mapear resultados
        for agent_name in agent_names_ordered:
            agent = self.agents[agent_name]
            agent_tasks.append(self._process_with_agent(agent_name, agent, task, context))
        
        # return_exceptions=True fará com que asyncio.gather retorne a exceção em vez de levantá-la
        results_from_gather = await asyncio.gather(*agent_tasks, return_exceptions=True)
        
        processed_results = []
        any_success = False
        all_success = True

        for i, result_or_exception in enumerate(results_from_gather):
            agent_name = agent_names_ordered[i]
            if isinstance(result_or_exception, Exception):
                logger.error(f"Padrão Concorrente: Agente {agent_name} falhou com exceção: {result_or_exception}", exc_info=result_or_exception)
                processed_results.append({
                    "agent": agent_name,
                    "success": False,
                    "input": task, # Adiciona o input original para contexto
                    "error": f"Agente {agent_name} falhou: {result_or_exception}"
                })
                all_success = False
            elif isinstance(result_or_exception, dict) and not result_or_exception.get("success"):
                # Caso _process_with_agent retorne um dict de falha (já tratado)
                logger.warning(f"Padrão Concorrente: Agente {agent_name} retornou falha: {result_or_exception.get('error')}")
                processed_results.append(result_or_exception)
                all_success = False
            else: # Sucesso
                logger.info(f"Padrão Concorrente: Agente {agent_name} completou com sucesso.")
                processed_results.append(result_or_exception)
                any_success = True
        
        final_status = any_success # Considera sucesso se pelo menos um agente funcionou.
                                   # Ou poderia ser all_success, dependendo do requisito.
        return {
            "success": final_status,
            "pattern": "concurrent",
            "results": processed_results,
            "all_agents_succeeded": all_success # Informação adicional
        }
    
    async def _group_chat_orchestration(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Implementa orquestração de chat em grupo"""
        conversation_history = [{"role": "user", "content": task, "timestamp": datetime.now().isoformat()}]
        iteration = 0
        
        agent_names = list(self.agents.keys())
        if not agent_names: # Deve ser pego no orchestrate, mas como segurança
            logger.error("Padrão Group Chat: Nenhum agente disponível para o chat.")
            return {"success": False, "pattern": "group_chat", "error": "Nenhum agente para o chat."}

        while iteration < self.max_iterations:
            current_agent_name = agent_names[iteration % len(agent_names)]
            current_agent = self.agents[current_agent_name]
            
            chat_context = context.copy()
            chat_context["conversation_history"] = conversation_history
            
            try:
                logger.info(f"Padrão Group Chat: Agente {current_agent_name} processando. Iteração: {iteration + 1}")
                response = await current_agent.process(task, chat_context)

                conversation_history.append({
                    "role": "agent",
                    "agent": current_agent_name,
                    "content": response,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Critério de parada mais robusto pode ser necessário
                if "finalizado" in response.lower() or "concluído" in response.lower():
                    logger.info(f"Padrão Group Chat: Conversa concluída por {current_agent_name}.")
                    break
            except RuntimeError as e:
                logger.error(f"Padrão Group Chat: Erro com agente {current_agent_name}: {e}", exc_info=True)
                conversation_history.append({
                    "role": "system",
                    "agent": current_agent_name,
                    "content": f"Erro ao processar com {current_agent_name}: {e}",
                    "error": True,
                    "timestamp": datetime.now().isoformat()
                })
                # Decide se o chat deve parar ou tentar com outro agente
                # Por ora, vamos parar para evitar loops infinitos de erro.
                return {
                    "success": False,
                    "pattern": "group_chat",
                    "conversation_history": conversation_history,
                    "iterations": iteration + 1,
                    "error": f"Falha no agente {current_agent_name} durante o chat."
                }
            iteration += 1
        
        if iteration == self.max_iterations:
            logger.warning(f"Padrão Group Chat: Máximo de iterações ({self.max_iterations}) atingido.")

        return {
            "success": True, # Mesmo que atinja max_iterations, a orquestração em si não falhou.
            "pattern": "group_chat",
            "conversation_history": conversation_history,
            "iterations": iteration # iteration já foi incrementado ou é o valor final
        }

    async def _handoff_orchestration(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Implementa orquestração com handoff"""
        agent_names = list(self.agents.keys())
        if not agent_names:
            logger.error("Padrão Handoff: Nenhum agente disponível.")
            return {"success": False, "pattern": "handoff", "error": "Nenhum agente para handoff."}

        current_agent_name = agent_names[0]
        handoff_chain = []
        iteration = 0
        
        processed_task = task # A tarefa pode evoluir ou ser redefinida

        while iteration < self.max_iterations:
            if current_agent_name not in self.agents:
                logger.error(f"Padrão Handoff: Agente '{current_agent_name}' não encontrado. Interrompendo.")
                return {
                    "success": False,
                    "pattern": "handoff",
                    "handoff_chain": handoff_chain,
                    "error": f"Agente de handoff '{current_agent_name}' não existe."
                }
            current_agent = self.agents[current_agent_name]
            
            handoff_context = context.copy()
            handoff_context["available_agents"] = agent_names
            handoff_context["current_agent"] = current_agent_name
            handoff_context["handoff_history"] = [h.get("agent") for h in handoff_chain] # Passa histórico de agentes

            try:
                logger.info(f"Padrão Handoff: Agente {current_agent_name} processando. Iteração: {iteration + 1}")
                response = await current_agent.process(processed_task, handoff_context)

                handoff_chain.append({
                    "agent": current_agent_name,
                    "input_task": processed_task, # Logar a tarefa como vista pelo agente
                    "response": response,
                    "iteration": iteration,
                    "timestamp": datetime.now().isoformat()
                })
                
                # A resposta do agente pode modificar a tarefa para o próximo
                # Ex: "Tarefa concluída. Próximo passo para [AgenteX]: Analisar resultado Y"
                # Aqui, a lógica de extrair a nova tarefa e o próximo agente da 'response' seria crucial.
                # Por simplicidade, vamos assumir que a 'response' pode conter o nome do próximo agente.
                # E a 'processed_task' pode ser a 'response' ou parte dela.

                next_agent_candidate = self._determine_next_agent(response, current_agent_name)

                if next_agent_candidate and next_agent_candidate != current_agent_name:
                    logger.info(f"Padrão Handoff: Handoff de {current_agent_name} para {next_agent_candidate}.")
                    current_agent_name = next_agent_candidate
                    # A 'response' do agente anterior pode se tornar a 'processed_task' para o próximo,
                    # ou uma parte dela. Esta lógica precisa ser bem definida.
                    # Exemplo simples: processed_task = response
                else:
                    logger.info(f"Padrão Handoff: Concluído pelo agente {current_agent_name} ou sem handoff claro.")
                    break
            except RuntimeError as e:
                logger.error(f"Padrão Handoff: Erro com agente {current_agent_name}: {e}", exc_info=True)
                handoff_chain.append({
                    "agent": current_agent_name,
                    "input_task": processed_task,
                    "response": None,
                    "iteration": iteration,
                    "error": f"Agente {current_agent_name} falhou: {e}",
                    "timestamp": datetime.now().isoformat()
                })
                return {
                    "success": False,
                    "pattern": "handoff",
                    "handoff_chain": handoff_chain,
                    "final_agent": current_agent_name,
                    "error": f"Falha no agente {current_agent_name} durante handoff."
                }
            iteration += 1

        if iteration == self.max_iterations:
            logger.warning(f"Padrão Handoff: Máximo de iterações ({self.max_iterations}) atingido.")

        return {
            "success": True,
            "pattern": "handoff",
            "handoff_chain": handoff_chain,
            "final_agent": current_agent_name, # O último agente que processou
            "final_output": handoff_chain[-1]["response"] if handoff_chain else None
        }

    async def _process_with_agent(self, agent_name: str, agent: BaseAgent, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Processa uma tarefa com um agente específico, usado principalmente por _concurrent_orchestration."""
        logger.debug(f"Processando tarefa '{task[:50]}...' com agente '{agent_name}' individualmente.")
        try:
            # Adiciona o nome do agente ao contexto para que ele possa saber quem é, se necessário
            agent_specific_context = context.copy()
            # agent_specific_context["_executing_agent_name_"] = agent_name # Exemplo

            result = await agent.process(task, agent_specific_context)
            logger.info(f"Agente '{agent_name}' completou tarefa individual com sucesso.")
            return {
                "agent": agent_name,
                "success": True,
                "input": task,
                "output": result
            }
        except RuntimeError as e: # Erros esperados do processamento do agente
            logger.error(f"Erro de Runtime ao processar com agente '{agent_name}': {e}", exc_info=True)
            # Não levantar exceção aqui, pois asyncio.gather(*, return_exceptions=True) espera o valor.
            # Ou, se não usar return_exceptions, esta exceção seria propagada.
            # No caso de return_exceptions=True, podemos retornar um dict de erro.
            return {
                "agent": agent_name,
                "success": False,
                "input": task,
                "error": f"RuntimeError: {e}" # Inclui o tipo de erro
            }
        except Exception as e: # Outros erros inesperados
            logger.error(f"Erro inesperado ao processar com agente '{agent_name}': {e}", exc_info=True)
            return {
                "agent": agent_name,
                "success": False,
                "input": task,
                "error": f"UnexpectedError: {e}"
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