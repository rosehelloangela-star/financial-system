# backend/rag/kg_visualizer.py
"""
知识图谱可视化 - 生成HTML和JSON文件
"""
import logging
import json
from typing import Dict, List
from pathlib import Path
import networkx as nx
from datetime import datetime
 
logger = logging.getLogger(__name__)
 
 
class KGVisualizer:
    """知识图谱可视化器"""
    
    def __init__(self, output_dir: str = "knowledge_graphs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def save_graph(
        self,
        entities: List[Dict],
        relationships: List[Dict],
        filename: str,
        metadata: Dict = None
    ) -> Dict[str, str]:
        """
        保存知识图谱到文件
        
        Returns:
            {
                "json_path": str,
                "html_path": str,
                "graphml_path": str
            }
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{filename}_{timestamp}"
        
        # 1. 保存JSON格式
        json_path = self._save_json(entities, relationships, base_name, metadata)
        
        # 2. 保存HTML可视化
        html_path = self._save_html(entities, relationships, base_name)
        
        # 3. 保存GraphML（可用于Gephi等工具）
        graphml_path = self._save_graphml(entities, relationships, base_name)
        
        logger.info(f"✅ Knowledge graph saved to {self.output_dir}")
        
        return {
            "json_path": str(json_path),
            "html_path": str(html_path),
            "graphml_path": str(graphml_path)
        }
    
    def _save_json(
        self,
        entities: List[Dict],
        relationships: List[Dict],
        base_name: str,
        metadata: Dict
    ) -> Path:
        """保存JSON格式"""
        json_path = self.output_dir / f"{base_name}.json"
        
        data = {
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "entities": entities,
            "relationships": relationships,
            "stats": {
                "num_entities": len(entities),
                "num_relationships": len(relationships)
            }
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 JSON saved: {json_path}")
        return json_path
    
    # backend/rag/kg_visualizer.py (修改_save_html方法)
 
    def _save_html(
        self,
        entities: List[Dict],
        relationships: List[Dict],
        base_name: str
    ) -> Path:
        """保存HTML可视化（带重要性显示）"""
        html_path = self.output_dir / f"{base_name}.html"
        
        # 构建vis.js格式的数据
        nodes = []
        node_ids = set()
        
        for ent in entities:
            node_id = ent.get("text", "")
            if node_id and node_id not in node_ids:
                importance = ent.get("importance", 1.0)
                
                # 根据重要性设置节点大小和颜色
                node_size = 10 + importance * 3  # 10-40
                
                # 颜色映射
                entity_type = ent.get("type", "default")
                color_map = {
                    "COMPANY": "#3498db",
                    "PERSON": "#e74c3c",
                    "METRIC": "#2ecc71",
                    "NUMBER": "#f39c12",
                    "DATE": "#9b59b6",
                    "PRODUCT": "#1abc9c",
                    "LOCATION": "#34495e",
                    "EVENT": "#e67e22"
                }
                color = color_map.get(entity_type, "#95a5a6")
                
                nodes.append({
                    "id": node_id,
                    "label": node_id[:50],
                    "title": f"{entity_type}\nImportance: {importance:.1f}",
                    "group": entity_type,
                    "size": node_size,
                    "color": color,
                    "importance": importance
                })
                node_ids.add(node_id)
        
        # 只显示重要节点（importance > 2）和它们的关系
        important_nodes = {n["id"] for n in nodes if n.get("importance", 0) > 2}
        
        edges = []
        for rel in relationships:
            source = rel.get("source", "")
            target = rel.get("target", "")
            
            # 只显示连接重要节点的关系
            if source in important_nodes or target in important_nodes:
                edges.append({
                    "from": source,
                    "to": target,
                    "label": rel.get("relation", "")[:20],
                    "title": rel.get("context", "")[:100],
                    "arrows": "to"
                })
        
        # HTML模板（增强版）
        html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Knowledge Graph - {base_name}</title>
        <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background: #f5f5f5;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
            }}
            h1 {{
                color: #2c3e50;
                text-align: center;
            }}
            #mynetwork {{
                width: 100%;
                height: 700px;
                border: 2px solid #ddd;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            #info {{
                margin-bottom: 20px;
                padding: 20px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 15px;
            }}
            .stat-item {{
                padding: 15px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 5px;
                text-align: center;
            }}
            .stat-value {{
                font-size: 32px;
                font-weight: bold;
                margin-bottom: 5px;
            }}
            .stat-label {{
                font-size: 14px;
                opacity: 0.9;
            }}
            .legend {{
                display: flex;
                flex-wrap: wrap;
                gap: 15px;
                margin-top: 20px;
                padding: 15px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .legend-item {{
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .legend-color {{
                width: 20px;
                height: 20px;
                border-radius: 50%;
            }}
            .controls {{
                margin-top: 15px;
                text-align: center;
            }}
            button {{
                padding: 10px 20px;
                margin: 5px;
                background: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 14px;
            }}
            button:hover {{
                background: #2980b9;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Knowledge Graph: {base_name}</h1>
            
            <div id="info">
                <h3>Statistics</h3>
                <div class="stats">
                    <div class="stat-item">
                        <div class="stat-value">{len(entities)}</div>
                        <div class="stat-label">Total Entities</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{len(relationships)}</div>
                        <div class="stat-label">Total Relationships</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{len(nodes)}</div>
                        <div class="stat-label">Visualized Nodes</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{len(edges)}</div>
                        <div class="stat-label">Visualized Edges</div>
                    </div>
                </div>
                
                <div class="legend">
                    <strong>Entity Types:</strong>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #3498db;"></div>
                        <span>COMPANY</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #e74c3c;"></div>
                        <span>PERSON</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #2ecc71;"></div>
                        <span>METRIC</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #f39c12;"></div>
                        <span>NUMBER</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #9b59b6;"></div>
                        <span>DATE</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background: #1abc9c;"></div>
                        <span>PRODUCT</span>
                    </div>
                </div>
                
                <div class="controls">
                    <button onclick="network.fit()">Fit to Screen</button>
                    <button onclick="network.stabilize()">Stabilize</button>
                    <button onclick="togglePhysics()">Toggle Physics</button>
                </div>
            </div>
            
            <div id="mynetwork"></div>
        </div>
        
        <script>
            var nodes = new vis.DataSet({json.dumps(nodes)});
            var edges = new vis.DataSet({json.dumps(edges)});
            
            var container = document.getElementById('mynetwork');
            var data = {{
                nodes: nodes,
                edges: edges
            }};
            
            var options = {{
                nodes: {{
                    shape: 'dot',
                    font: {{
                        size: 14,
                        color: '#333'
                    }},
                    borderWidth: 2,
                    shadow: true
                }},
                edges: {{
                    width: 2,
                    arrows: {{
                        to: {{enabled: true, scaleFactor: 0.5}}
                    }},
                    smooth: {{
                        type: 'continuous'
                    }},
                    font: {{
                        size: 11,
                        align: 'middle'
                    }},
                    color: {{
                        color: '#848484',
                        highlight: '#3498db'
                    }}
                }},
                physics: {{
                    enabled: true,
                    barnesHut: {{
                        gravitationalConstant: -5000,
                        centralGravity: 0.3,
                        springLength: 150,
                        springConstant: 0.04
                    }},
                    stabilization: {{
                        iterations: 200
                    }}
                }},
                interaction: {{
                    hover: true,
                    tooltipDelay: 100,
                    navigationButtons: true,
                    keyboard: true
                }}
            }};
            
            var network = new vis.Network(container, data, options);
            var physicsEnabled = true;
            
            function togglePhysics() {{
                physicsEnabled = !physicsEnabled;
                network.setOptions({{physics: {{enabled: physicsEnabled}}}});
            }}
            
            // 点击节点高亮连接
            network.on("selectNode", function(params) {{
                var nodeId = params.nodes[0];
                var connectedNodes = network.getConnectedNodes(nodeId);
                var connectedEdges = network.getConnectedEdges(nodeId);
                
                console.log("Selected:", nodeId);
                console.log("Connected to:", connectedNodes);
            }});
            
            // 稳定后关闭物理引擎（提高性能）
            network.once("stabilizationIterationsDone", function() {{
                network.setOptions({{physics: false}});
                physicsEnabled = false;
            }});
        </script>
    </body>
    </html>
    """
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"🌐 HTML saved: {html_path}")
        return html_path
    
    def _save_graphml(
        self,
        entities: List[Dict],
        relationships: List[Dict],
        base_name: str
    ) -> Path:
        """保存GraphML格式（可用于Gephi等专业工具）"""
        graphml_path = self.output_dir / f"{base_name}.graphml"
        
        # 使用networkx创建图
        G = nx.DiGraph()
        
        # 添加节点
        for ent in entities:
            node_id = ent.get("text", "")
            if node_id:
                G.add_node(
                    node_id,
                    type=ent.get("type", ""),
                    label=node_id
                )
        
        # 添加边
        for rel in relationships:
            source = rel.get("source", "")
            target = rel.get("target", "")
            if source and target:
                G.add_edge(
                    source,
                    target,
                    relation=rel.get("relation", ""),
                    context=rel.get("context", "")
                )
        
        # 保存
        nx.write_graphml(G, graphml_path)
        
        logger.info(f"📊 GraphML saved: {graphml_path}")
        return graphml_path
 
 
kg_visualizer = KGVisualizer()