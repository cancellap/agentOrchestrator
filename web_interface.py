"""
Interface Web para o Sistema de Orquestração de Agentes
Aplicação Flask para interação com o sistema
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import asyncio
import logging
import os
from datetime import datetime
import json

from orchestration_system import OrchestrationSystem, OrchestrationWorkflow

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cria aplicação Flask
app = Flask(__name__)
CORS(app)  # Permite CORS para todas as rotas

# Sistema de orquestração global
orchestration_system = None
workflow_manager = None


async def initialize_system():
    """Inicializa o sistema de orquestração"""
    global orchestration_system, workflow_manager
    
    try:
        orchestration_system = OrchestrationSystem()
        await orchestration_system.initialize()
        
        workflow_manager = OrchestrationWorkflow(orchestration_system)
        
        logger.info("Sistema de orquestração inicializado com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao inicializar sistema: {str(e)}")
        return False


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
def get_status():
    """Retorna status do sistema"""
    if orchestration_system is None:
        return jsonify({"error": "Sistema não inicializado"}), 500
    
    try:
        status = orchestration_system.get_system_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/agents')
def get_agents():
    """Retorna agentes disponíveis"""
    if orchestration_system is None:
        return jsonify({"error": "Sistema não inicializado"}), 500
    
    try:
        agents = orchestration_system.get_available_agents()
        return jsonify({"agents": agents})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/orchestrators', methods=['GET', 'POST'])
def handle_orchestrators():
    """Gerencia orquestradores"""
    if orchestration_system is None:
        return jsonify({"error": "Sistema não inicializado"}), 500
    
    if request.method == 'GET':
        try:
            orchestrators = orchestration_system.get_orchestrators()
            return jsonify({"orchestrators": orchestrators})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            
            # Valida dados
            required_fields = ['name', 'pattern', 'agent_names']
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"Campo obrigatório: {field}"}), 400
            
            # Cria orquestrador
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            orchestrator_name = loop.run_until_complete(
                orchestration_system.create_orchestrator(
                    name=data['name'],
                    pattern=data['pattern'],
                    agent_names=data['agent_names'],
                    max_iterations=data.get('max_iterations', 10),
                    timeout=data.get('timeout', 300)
                )
            )
            
            return jsonify({
                "success": True,
                "orchestrator_name": orchestrator_name,
                "message": f"Orquestrador '{orchestrator_name}' criado com sucesso"
            })
            
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/execute', methods=['POST'])
def execute_orchestration():
    """Executa uma orquestração"""
    if orchestration_system is None:
        return jsonify({"error": "Sistema não inicializado"}), 500
    
    try:
        data = request.get_json()
        
        # Valida dados
        required_fields = ['orchestrator_name', 'task']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Campo obrigatório: {field}"}), 400
        
        # Executa orquestração
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            orchestration_system.execute_orchestration(
                orchestrator_name=data['orchestrator_name'],
                task=data['task'],
                context=data.get('context')
            )
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/metrics')
def get_metrics():
    """Retorna métricas do sistema"""
    if orchestration_system is None:
        return jsonify({"error": "Sistema não inicializado"}), 500
    
    try:
        metrics = orchestration_system.get_metrics()
        return jsonify({"metrics": metrics})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/workflows', methods=['GET', 'POST'])
def handle_workflows():
    """Gerencia workflows"""
    if workflow_manager is None:
        return jsonify({"error": "Sistema não inicializado"}), 500
    
    if request.method == 'GET':
        try:
            workflows = workflow_manager.get_workflows()
            return jsonify({"workflows": workflows})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            
            workflow_manager.define_workflow(
                name=data['name'],
                steps=data['steps'],
                description=data.get('description', '')
            )
            
            return jsonify({
                "success": True,
                "message": f"Workflow '{data['name']}' definido com sucesso"
            })
            
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500


def run_app():
    """Executa a aplicação"""
    # Inicializa sistema
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    success = loop.run_until_complete(initialize_system())
    
    if not success:
        print("Erro ao inicializar sistema. Verifique as configurações.")
        return
    
    # Executa aplicação Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    run_app()

