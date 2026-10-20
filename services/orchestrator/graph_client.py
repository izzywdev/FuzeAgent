"""
graph_client.py
FuzeInfra Neo4j Knowledge Graph client for FuzeAgent.
Performs entity-relation upserts, 2-hop neighborhood traversals, and GraphRAG augmentation.
"""

import os
import logging
from typing import Dict, Any, List, Optional, Set, Tuple

try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None

logger = logging.getLogger(__name__)

NEO4J_URL = os.environ.get("NEO4J_URL", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password123")

class BrainGraphClient:
    def __init__(self, uri: str = NEO4J_URL, user: str = NEO4J_USER, password: str = NEO4J_PASSWORD):
        self.uri = uri
        self.user = user
        self.password = password
        self._driver = None
        if GraphDatabase:
            try:
                self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            except Exception as e:
                logger.warning(f"BrainGraphClient: Could not connect to FuzeInfra Neo4j: {e}")

    @property
    def is_available(self) -> bool:
        return self._driver is not None

    def upsert_entities_and_relations(
        self,
        brain_id: str,
        document_id: str,
        entities: List[Dict[str, str]],
        relations: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Persists extracted entities and relationships into the Neo4j Knowledge Graph.
        entities: [{"name": "AuthService", "type": "Service"}, ...]
        relations: [{"source": "AuthService", "relation": "DEPENDS_ON", "target": "PostgreSQL"}, ...]
        """
        if not self._driver:
            return {"status": "mock", "entities_count": len(entities), "relations_count": len(relations)}

        with self._driver.session() as session:
            # 1. Upsert document node
            session.run("""
                MERGE (d:Document {id: $doc_id})
                SET d.brain_id = $brain_id, d.updated_at = datetime()
            """, doc_id=document_id, brain_id=brain_id)

            # 2. Upsert entities and link to document
            for ent in entities:
                name = ent.get("name", "").strip()
                etype = ent.get("type", "Concept").strip()
                if not name:
                    continue
                session.run("""
                    MERGE (e:Entity {brain_id: $brain_id, name: $name})
                    ON CREATE SET e.type = $etype, e.created_at = datetime()
                    ON MATCH SET e.type = $etype, e.updated_at = datetime()
                    WITH e
                    MATCH (d:Document {id: $doc_id})
                    MERGE (d)-[:MENTIONS]->(e)
                """, brain_id=brain_id, name=name, etype=etype, doc_id=document_id)

            # 3. Upsert relations between entities
            for rel in relations:
                src = rel.get("source", "").strip()
                tgt = rel.get("target", "").strip()
                rtype = rel.get("relation", "RELATES_TO").upper().replace(" ", "_")
                if not src or not tgt:
                    continue
                # Sanitize relation type for Cypher
                clean_rtype = "".join(c for c in rtype if c.isalnum() or c == "_") or "RELATES_TO"
                cypher = f"""
                    MATCH (s:Entity {{brain_id: $brain_id, name: $src}})
                    MATCH (t:Entity {{brain_id: $brain_id, name: $tgt}})
                    MERGE (s)-[r:{clean_rtype} {{brain_id: $brain_id}}]->(t)
                    SET r.updated_at = datetime()
                """
                session.run(cypher, brain_id=brain_id, src=src, tgt=tgt)

        return {
            "status": "persisted",
            "brain_id": brain_id,
            "document_id": document_id,
            "entities_upserted": len(entities),
            "relations_upserted": len(relations)
        }

    def traverse_2hop_neighborhood(self, brain_id: str, seed_entities: List[str]) -> List[Dict[str, Any]]:
        """
        Expands the graph 2 hops outward from identified seed entities for GraphRAG context.
        Returns linked entities, relationship verbs, and connected documents.
        """
        if not self._driver or not seed_entities:
            return []

        cypher = """
            MATCH (e:Entity {brain_id: $brain_id})
            WHERE e.name IN $seed_entities
            OPTIONAL MATCH (e)-[r]-(neighbor:Entity {brain_id: $brain_id})
            OPTIONAL MATCH (neighbor)-[r2]-(second_hop:Entity {brain_id: $brain_id})
            RETURN e.name AS seed,
                   type(r) AS rel1,
                   neighbor.name AS neighbor_name,
                   neighbor.type AS neighbor_type,
                   type(r2) AS rel2,
                   second_hop.name AS hop2_name,
                   second_hop.type AS hop2_type
            LIMIT 50
        """
        results = []
        with self._driver.session() as session:
            rows = session.run(cypher, brain_id=brain_id, seed_entities=seed_entities).data()
            for row in rows:
                if row.get("neighbor_name"):
                    results.append({
                        "path": f"({row['seed']}) -[:{row['rel1']}]-> ({row['neighbor_name']} [{row.get('neighbor_type')}])",
                        "target": row["neighbor_name"],
                        "hop": 1
                    })
                if row.get("hop2_name"):
                    results.append({
                        "path": f"({row['neighbor_name']}) -[:{row['rel2']}]-> ({row['hop2_name']} [{row.get('hop2_type')}])",
                        "target": row["hop2_name"],
                        "hop": 2
                    })
        return results

# Global graph client instance
brain_graph = BrainGraphClient()
