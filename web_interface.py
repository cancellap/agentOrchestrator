"""
Interface Web para o Sistema de Orquestração de Agentes
Aplicação Flask para interação com o sistema
"""

from flask import Flask, request, jsonify, render_template_string, make_response
from flask_cors import CORS
import asyncio
import logging
import os
from datetime import datetime
import json # Embora json seja usado implicitamente por jsonify, pode ser útil para carregar/validar.

from orchestration_system import OrchestrationSystem, OrchestrationWorkflow
# Importar ConfigManager para obter configurações de logging, se necessário para configurar antes do app.
from config_utils import ConfigManager, LoggingUtils

# Configuração de logging inicial (pode ser sobrescrita pela config do OrchestrationSystem)
# É importante configurar o logging o mais cedo possível.
# Se OrchestrationSystem configura o logging, esta configuração pode ser redundante ou um fallback.
# Vamos assumir que OrchestrationSystem.initialize() irá configurar o logging principal.
logger = logging.getLogger(__name__) # Logger específico para a interface web


# Cria aplicação Flask
app = Flask(__name__)
CORS(app)  # Permite CORS para todas as rotas

# Sistema de orquestração global - será inicializado em initialize_system
orchestration_system: Optional[OrchestrationSystem] = None
workflow_manager: Optional[OrchestrationWorkflow] = None
system_initialized_successfully = False


async def initialize_system_globally():
    """Inicializa o sistema de orquestração globalmente."""
    global orchestration_system, workflow_manager, system_initialized_successfully
    
    if orchestration_system is not None:
        logger.info("Sistema de orquestração já inicializado.")
        return

    try:
        # Primeiro, configurar o logging usando ConfigManager, se o OrchestrationSystem não o fizer primeiro.
        # Se OrchestrationSystem já configura, esta parte pode ser ajustada.
        # temp_config_manager = ConfigManager()
        # LoggingUtils.setup_logging(temp_config_manager.config.get("logging", {}))
        # logger.info("Logging configurado para a interface web (tentativa inicial).")

        logger.info("Iniciando a inicialização do sistema de orquestração...")
        temp_system = OrchestrationSystem() # OrchestrationSystem agora configura o logging.
        await temp_system.initialize() # Pode levantar RuntimeError
        
        orchestration_system = temp_system
        workflow_manager = OrchestrationWorkflow(orchestration_system)
        system_initialized_successfully = True
        logger.info("Sistema de orquestração e workflow manager inicializados com sucesso globalmente.")
        
    except RuntimeError as rte:
        logger.critical(f"Falha crítica ao inicializar o sistema de orquestração global: {rte}", exc_info=True)
        system_initialized_successfully = False
        # A aplicação pode continuar rodando, mas os endpoints que dependem do sistema falharão.
    except Exception as e:
        logger.critical(f"Erro inesperado e crítico durante a inicialização global do sistema: {e}", exc_info=True)
        system_initialized_successfully = False

# Decorador para verificar se o sistema foi inicializado
from functools import wraps

def require_system_initialized(f):
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        if not system_initialized_successfully or orchestration_system is None:
            logger.error(f"Endpoint {request.path} chamado, mas o sistema não foi inicializado corretamente.")
            return jsonify({"success": False, "error": "O sistema de orquestração não está disponível ou falhou ao inicializar."}), 503 # Service Unavailable
        return await f(*args, **kwargs)
    return decorated_function

# Template HTML para interface web
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Orquestrador de Agentes</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        h1, h2 {
            color: #333;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input, select, textarea {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        textarea {
            height: 100px;
            resize: vertical;
        }
        button {
            background-color: #007bff;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 10px;
        }
        button:hover {
            background-color: #0056b3;
        }
        .result {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 15px;
            margin-top: 15px;
            white-space: pre-wrap;
        }
        .success {
            border-color: #28a745;
            background-color: #d4edda;
        }
        .error {
            border-color: #dc3545;
            background-color: #f8d7da;
        }
        .agent-card {
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
            margin-bottom: 10px;
            background-color: #f9f9f9;
        }
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        .metric-card {
            background: #e9ecef;
            padding: 15px;
            border-radius: 4px;
            text-align: center;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
        }
    </style>
</head>
<body>
    <h1>🤖 Orquestrador de Agentes IA</h1>
    
    <!-- Status do Sistema -->
    <div class="container">
        <h2>Status do Sistema</h2>
        <button onclick="loadSystemStatus()">Atualizar Status</button>
        <div id="systemStatus" class="result"></div>
    </div>
    
    <!-- Agentes Disponíveis -->
    <div class="container">
        <h2>Agentes Disponíveis</h2>
        <button onclick="loadAgents()">Carregar Agentes</button>
        <div id="agentsList"></div>
    </div>
    
    <!-- Criar Orquestrador -->
    <div class="container">
        <h2>Criar Orquestrador</h2>
        <form id="createOrchestratorForm">
            <div class="form-group">
                <label for="orchestratorName">Nome do Orquestrador:</label>
                <input type="text" id="orchestratorName" required>
            </div>
            <div class="form-group">
                <label for="orchestrationPattern">Padrão de Orquestração:</label>
                <select id="orchestrationPattern" required>
                    <option value="sequential">Sequencial</option>
                    <option value="concurrent">Concorrente</option>
                    <option value="group_chat">Chat em Grupo</option>
                    <option value="handoff">Handoff</option>
                </select>
            </div>
            <div class="form-group">
                <label for="selectedAgents">Agentes (separados por vírgula):</label>
                <input type="text" id="selectedAgents" placeholder="Analista,Redator" required>
            </div>
            <button type="submit">Criar Orquestrador</button>
        </form>
        <div id="createResult" class="result" style="display:none;"></div>
    </div>
    
    <!-- Executar Orquestração -->
    <div class="container">
        <h2>Executar Orquestração</h2>
        <form id="executeForm">
            <div class="form-group">
                <label for="orchestratorSelect">Orquestrador:</label>
                <select id="orchestratorSelect" required>
                    <option value="">Selecione um orquestrador</option>
                </select>
                <button type="button" onclick="loadOrchestrators()">Carregar Orquestradores</button>
            </div>
            <div class="form-group">
                <label for="taskInput">Tarefa:</label>
                <textarea id="taskInput" placeholder="Descreva a tarefa que deseja executar..." required></textarea>
            </div>
            <div class="form-group">
                <label for="contextInput">Contexto (opcional, JSON):</label>
                <textarea id="contextInput" placeholder='{"key": "value"}'></textarea>
            </div>
            <button type="submit">Executar Orquestração</button>
        </form>
        <div id="executeResult" class="result" style="display:none;"></div>
    </div>
    
    <!-- Métricas -->
    <div class="container">
        <h2>Métricas do Sistema</h2>
        <button onclick="loadMetrics()">Atualizar Métricas</button>
        <div id="metricsDisplay" class="metrics"></div>
    </div>

    <script>
        // Funções JavaScript para interação com a API
        
        async function makeRequest(url, method = 'GET', data = null) {
            const options = {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                }
            };
            
            if (data) {
                options.body = JSON.stringify(data);
            }
            
            try {
                const response = await fetch(url, options);
                const result = await response.json();
                return result;
            } catch (error) {
                console.error('Erro na requisição:', error);
                return { error: error.message };
            }
        }
        
        async function loadSystemStatus() {
            const result = await makeRequest('/api/status');
            const statusDiv = document.getElementById('systemStatus');
            statusDiv.textContent = JSON.stringify(result, null, 2);
            statusDiv.className = 'result';
        }
        
        async function loadAgents() {
            const result = await makeRequest('/api/agents');
            const agentsDiv = document.getElementById('agentsList');
            
            if (result.agents) {
                agentsDiv.innerHTML = result.agents.map(agent => `
                    <div class="agent-card">
                        <h4>${agent.name}</h4>
                        <p>${agent.description}</p>
                        <p><strong>Capacidades:</strong> ${agent.capabilities.join(', ')}</p>
                    </div>
                `).join('');
            } else {
                agentsDiv.innerHTML = '<p>Nenhum agente disponível</p>';
            }
        }
        
        async function loadOrchestrators() {
            const result = await makeRequest('/api/orchestrators');
            const select = document.getElementById('orchestratorSelect');
            
            select.innerHTML = '<option value="">Selecione um orquestrador</option>';
            
            if (result.orchestrators) {
                result.orchestrators.forEach(orch => {
                    const option = document.createElement('option');
                    option.value = orch.name;
                    option.textContent = `${orch.name} (${orch.pattern})`;
                    select.appendChild(option);
                });
            }
        }
        
        async function loadMetrics() {
            const result = await makeRequest('/api/metrics');
            const metricsDiv = document.getElementById('metricsDisplay');
            
            if (result.metrics) {
                const metrics = result.metrics;
                metricsDiv.innerHTML = `
                    <div class="metric-card">
                        <div class="metric-value">${metrics.orchestrations_count}</div>
                        <div>Total de Orquestrações</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${metrics.successful_orchestrations}</div>
                        <div>Sucessos</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${metrics.failed_orchestrations}</div>
                        <div>Falhas</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${metrics.average_execution_time.toFixed(2)}s</div>
                        <div>Tempo Médio</div>
                    </div>
                `;
            }
        }
        
        // Event listeners para formulários
        document.getElementById('createOrchestratorForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const data = {
                name: document.getElementById('orchestratorName').value,
                pattern: document.getElementById('orchestrationPattern').value,
                agent_names: document.getElementById('selectedAgents').value.split(',').map(s => s.trim())
            };
            
            const result = await makeRequest('/api/orchestrators', 'POST', data);
            const resultDiv = document.getElementById('createResult');
            
            resultDiv.style.display = 'block';
            resultDiv.textContent = JSON.stringify(result, null, 2);
            resultDiv.className = result.success ? 'result success' : 'result error';
        });
        
        document.getElementById('executeForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            let context = null;
            const contextInput = document.getElementById('contextInput').value.trim();
            
            if (contextInput) {
                try {
                    context = JSON.parse(contextInput);
                } catch (error) {
                    alert('Contexto deve ser um JSON válido');
                    return;
                }
            }
            
            const data = {
                orchestrator_name: document.getElementById('orchestratorSelect').value,
                task: document.getElementById('taskInput').value,
                context: context
            };
            
            const result = await makeRequest('/api/execute', 'POST', data);
            const resultDiv = document.getElementById('executeResult');
            
            resultDiv.style.display = 'block';
            resultDiv.textContent = JSON.stringify(result, null, 2);
            resultDiv.className = result.success ? 'result success' : 'result error';
        });
        
        // Carrega dados iniciais
        window.onload = function() {
            loadSystemStatus();
            loadAgents();
            loadOrchestrators();
        };
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Página principal"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/status')
@require_system_initialized
async def get_status():
    """Retorna status do sistema"""
    # O orchestration_system é garantido pelo decorador
    try:
        status = orchestration_system.get_system_status()
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"Erro ao obter status do sistema: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"Erro interno ao processar status: {e}"}), 500


@app.route('/api/agents')
@require_system_initialized
async def get_agents():
    """Retorna agentes disponíveis"""
    try:
        agents = orchestration_system.get_available_agents()
        return jsonify({"agents": agents}), 200
    except Exception as e:
        logger.error(f"Erro ao obter lista de agentes: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"Erro interno ao buscar agentes: {e}"}), 500


@app.route('/api/orchestrators', methods=['GET', 'POST'])
@require_system_initialized
async def handle_orchestrators():
    """Gerencia orquestradores"""
    if request.method == 'GET':
        try:
            orchestrators = orchestration_system.get_orchestrators()
            return jsonify({"orchestrators": orchestrators}), 200
        except Exception as e:
            logger.error(f"Erro ao listar orquestradores: {e}", exc_info=True)
            return jsonify({"success": False, "error": f"Erro interno ao listar orquestradores: {e}"}), 500
    
    elif request.method == 'POST':
        if not request.is_json:
            logger.warning("Tentativa de criar orquestrador sem JSON.")
            return jsonify({"success": False, "error": "Requisição deve ser JSON."}), 400

        data = request.get_json()
        required_fields = ['name', 'pattern', 'agent_names']
        missing_fields = [field for field in required_fields if field not in data or not data[field]]

        if missing_fields:
            logger.warning(f"Tentativa de criar orquestrador com campos ausentes: {missing_fields}")
            return jsonify({"success": False, "error": f"Campos obrigatórios ausentes: {', '.join(missing_fields)}"}), 400

        if not isinstance(data['agent_names'], list) or not data['agent_names']:
             logger.warning(f"Tentativa de criar orquestrador '{data['name']}' com lista de agentes inválida.")
             return jsonify({"success": False, "error": "O campo 'agent_names' deve ser uma lista não vazia de nomes de agentes."}), 400

        try:
            # Não é necessário criar um novo loop de eventos aqui se o Flask estiver rodando com um executor async (como uvicorn/hypercorn)
            # ou se estivermos usando `await` diretamente em rotas async.
            # Se Flask estiver rodando em modo síncrono tradicional, precisaremos de `asyncio.run_coroutine_threadsafe` ou similar.
            # Para simplicidade com `app.run(debug=True)`, vamos assumir que o loop padrão do asyncio pode ser usado.
            # Em produção, um servidor ASGI como Uvicorn é recomendado para Flask async.
            # loop = asyncio.get_event_loop() # Obter loop existente
            
            orchestrator_name = await orchestration_system.create_orchestrator(
                name=str(data['name']),
                pattern=str(data['pattern']),
                agent_names=[str(an) for an in data['agent_names']], # Garante que são strings
                max_iterations=data.get('max_iterations'), # Passa None se não existir, OrchestrationSystem usará default
                timeout=data.get('timeout') # Passa None se não existir
            )
            
            return jsonify({
                "success": True,
                "orchestrator_name": orchestrator_name,
                "message": f"Orquestrador '{orchestrator_name}' criado com sucesso."
            }), 201 # Created
        except ValueError as ve: # Erros de validação de dados do OrchestrationSystem
            logger.warning(f"Erro de valor ao criar orquestrador '{data.get('name')}': {ve}")
            return jsonify({"success": False, "error": str(ve)}), 400
        except RuntimeError as rte: # Erros de runtime (e.g., falha ao registrar agente)
            logger.error(f"Erro de runtime ao criar orquestrador '{data.get('name')}': {rte}", exc_info=True)
            return jsonify({"success": False, "error": str(rte)}), 500
        except Exception as e: # Outros erros inesperados
            logger.critical(f"Erro inesperado e não tratado ao criar orquestrador '{data.get('name')}': {e}", exc_info=True)
            return jsonify({"success": False, "error": f"Erro interno no servidor ao criar orquestrador: {e}"}), 500


@app.route('/api/execute', methods=['POST'])
@require_system_initialized
async def execute_orchestration_endpoint(): # Renomeado para evitar conflito com a função importada
    """Executa uma orquestração"""
    if not request.is_json:
        return jsonify({"success": False, "error": "Requisição deve ser JSON."}), 400

    data = request.get_json()
    orchestrator_name = data.get('orchestrator_name')
    task = data.get('task')

    if not orchestrator_name or not task:
        missing = []
        if not orchestrator_name: missing.append('orchestrator_name')
        if not task: missing.append('task')
        return jsonify({"success": False, "error": f"Campos obrigatórios ausentes: {', '.join(missing)}"}), 400

    context_input = data.get('context')
    parsed_context = None
    if isinstance(context_input, str) and context_input.strip():
        try:
            parsed_context = json.loads(context_input)
        except json.JSONDecodeError as je:
            logger.warning(f"Contexto fornecido para orquestrador '{orchestrator_name}' não é JSON válido: {context_input[:100]}... Erro: {je}")
            return jsonify({"success": False, "error": f"Contexto fornecido não é um JSON válido: {je}"}), 400
    elif isinstance(context_input, dict):
        parsed_context = context_input
    
    try:
        # orchestration_system.execute_orchestration já retorna um dict
        result = await orchestration_system.execute_orchestration(
            orchestrator_name=str(orchestrator_name),
            task=str(task),
            context=parsed_context
        )
        
        # O resultado já contém 'success' e 'error' se aplicável
        status_code = 200 if result.get("success") else 400 # Ou 500 se for erro interno
        if not result.get("success") and "não encontrado" in result.get("error", "").lower():
            status_code = 404 # Not Found
        elif not result.get("success") and "crítico" in result.get("error", "").lower():
             status_code = 500 # Internal Server Error

        return jsonify(result), status_code
        
    except Exception as e: # Captura de segurança para erros não esperados na camada da API
        logger.critical(f"Erro crítico e inesperado na API /execute para '{orchestrator_name}': {e}", exc_info=True)
        return jsonify({"success": False, "error": f"Erro interno crítico no servidor ao executar orquestração: {e}"}), 500


@app.route('/api/metrics')
@require_system_initialized
async def get_metrics():
    """Retorna métricas do sistema"""
    try:
        metrics = orchestration_system.get_metrics()
        return jsonify({"metrics": metrics}), 200
    except Exception as e:
        logger.error(f"Erro ao obter métricas: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"Erro interno ao buscar métricas: {e}"}), 500


@app.route('/api/workflows', methods=['GET', 'POST'])
@require_system_initialized
async def handle_workflows_endpoint(): # Renomeado
    """Gerencia workflows"""
    # workflow_manager é garantido pelo decorador (se orchestration_system estiver ok)
    if workflow_manager is None: # Checagem extra, embora o decorador deva cobrir
         logger.error("Workflow manager não está disponível, embora o sistema pareça inicializado.")
         return jsonify({"success": False, "error": "Gerenciador de workflows não está disponível."}), 503

    if request.method == 'GET':
        try:
            workflows = workflow_manager.get_workflows()
            return jsonify({"workflows": workflows}), 200
        except Exception as e:
            logger.error(f"Erro ao listar workflows: {e}", exc_info=True)
            return jsonify({"success": False, "error": f"Erro interno ao listar workflows: {e}"}), 500
    
    elif request.method == 'POST':
        if not request.is_json:
            return jsonify({"success": False, "error": "Requisição deve ser JSON."}), 400
            
        data = request.get_json()
        required_fields = ['name', 'steps']
        missing_fields = [field for field in required_fields if field not in data or not data[field]]

        if missing_fields:
            return jsonify({"success": False, "error": f"Campos obrigatórios ausentes para definir workflow: {', '.join(missing_fields)}"}), 400

        if not isinstance(data['steps'], list) or not data['steps']:
             return jsonify({"success": False, "error": "O campo 'steps' deve ser uma lista não vazia de etapas do workflow."}), 400

        try:
            workflow_manager.define_workflow(
                name=str(data['name']),
                steps=data['steps'], # Validação mais profunda dos steps é feita em define_workflow
                description=str(data.get('description', ''))
            )
            return jsonify({
                "success": True,
                "message": f"Workflow '{data['name']}' definido com sucesso."
            }), 201
        except ValueError as ve:
            logger.warning(f"Erro de valor ao definir workflow '{data.get('name')}': {ve}")
            return jsonify({"success": False, "error": str(ve)}), 400
        except Exception as e:
            logger.error(f"Erro inesperado ao definir workflow '{data.get('name')}': {e}", exc_info=True)
            return jsonify({"success": False, "error": f"Erro interno ao definir workflow: {e}"}), 500

# Adicionar um endpoint para executar workflows
@app.route('/api/workflows/execute', methods=['POST'])
@require_system_initialized
async def execute_workflow_endpoint():
    if workflow_manager is None:
         logger.error("Workflow manager não está disponível.")
         return jsonify({"success": False, "error": "Gerenciador de workflows não está disponível."}), 503
    
    if not request.is_json:
        return jsonify({"success": False, "error": "Requisição deve ser JSON."}), 400
    
    data = request.get_json()
    workflow_name = data.get('workflow_name')
    initial_input = data.get('initial_input')

    if not workflow_name or not initial_input:
        missing = []
        if not workflow_name: missing.append('workflow_name')
        if not initial_input: missing.append('initial_input')
        return jsonify({"success": False, "error": f"Campos obrigatórios ausentes para executar workflow: {', '.join(missing)}"}), 400

    parsed_context = None
    context_input = data.get('context')
    if isinstance(context_input, str) and context_input.strip():
        try:
            parsed_context = json.loads(context_input)
        except json.JSONDecodeError as je:
            return jsonify({"success": False, "error": f"Contexto fornecido não é um JSON válido: {je}"}), 400
    elif isinstance(context_input, dict):
        parsed_context = context_input

    try:
        result = await workflow_manager.execute_workflow(
            workflow_name=str(workflow_name),
            initial_input=str(initial_input),
            context=parsed_context
        )
        status_code = 200 if result.get("success") else 400
        if not result.get("success") and "não encontrado" in result.get("error", "").lower():
            status_code = 404
        elif not result.get("success") and "crítico" in result.get("error", "").lower():
            status_code = 500

        return jsonify(result), status_code
    except Exception as e:
        logger.critical(f"Erro crítico e inesperado na API /workflows/execute para '{workflow_name}': {e}", exc_info=True)
        return jsonify({"success": False, "error": f"Erro interno crítico no servidor ao executar workflow: {e}"}), 500


def run_app(run_init_system=True): # Parâmetro para controlar a inicialização durante testes, por exemplo
    """Executa a aplicação Flask."""
    
    if run_init_system:
        # Inicializa o sistema de orquestração em um loop de eventos asyncio
        # Isso é crucial se o Flask estiver rodando em um ambiente que não gerencia o loop por padrão para tarefas de inicialização.
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed(): # Se o loop foi fechado por algum motivo (raro no início)
                asyncio.set_event_loop(asyncio.new_event_loop())
                loop = asyncio.get_event_loop()

            logger.info("Tentando inicializar o sistema de orquestração antes de rodar o app Flask...")
            loop.run_until_complete(initialize_system_globally()) # Renomeado

            if not system_initialized_successfully:
                logger.critical("O sistema de orquestração falhou ao inicializar. A aplicação pode não funcionar corretamente.")
                # Decide se deve parar a aplicação ou continuar com funcionalidade limitada.
                # Por agora, apenas loga e continua.
            else:
                logger.info("Sistema de orquestração parece ter sido inicializado com sucesso.")

        except Exception as e:
            logger.critical(f"Exceção não tratada durante a tentativa de inicialização do sistema antes de rodar o app: {e}", exc_info=True)
            # Considerar se deve impedir o app de rodar.

    # Executa aplicação Flask
    # Para produção, use um servidor WSGI/ASGI como Gunicorn/Uvicorn.
    # app.run() é principalmente para desenvolvimento.
    try:
        port = int(os.environ.get('PORT', 5000))
        # `debug=False` é mais seguro para qualquer ambiente que não seja estritamente desenvolvimento local.
        # O modo debug do Flask pode ter implicações de segurança e performance.
        # Além disso, o reloader do modo debug pode causar problemas com inicialização de asyncio.
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        logger.critical(f"Falha ao iniciar a aplicação Flask: {e}", exc_info=True)

if __name__ == '__main__':
    # Este bloco é executado quando o script é rodado diretamente.
    # É um bom lugar para inicializar tarefas que precisam acontecer uma vez no início.
    run_app()

