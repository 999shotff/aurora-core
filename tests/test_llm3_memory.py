"""LLM-3: Cognitive Memory — comprehensive tests."""

from __future__ import annotations

import time
import tempfile
import shutil

import pytest

from aurora.memory.schemas import (
    MemoryRecord,
    MemoryStatus,
    MemoryType,
    EntityReference,
    WorkingMemory,
    RelationshipType,
    EntityType,
    generate_memory_id,
)
from aurora.memory.store import MemoryStore
from aurora.memory.index import MemoryIndex
from aurora.memory.retrieval import MemoryRetriever
from aurora.memory.relationships import MemoryRelationshipGraph, MemoryRelationship
from aurora.memory.manager import MemoryManager


# ── Schema Tests ───────────────────────────────────────────────────────────


class TestMemoryRecord:
    def test_create_record(self) -> None:
        record = MemoryRecord(
            memory_id="mem-test-001",
            memory_type=MemoryType.EPISODIC,
            domain="market",
            title="Test Memory",
            content="Test content",
            source="test",
            provenance="test:unit",
            created_at=1000.0,
            updated_at=1000.0,
        )
        assert record.memory_id == "mem-test-001"
        assert record.memory_type == MemoryType.EPISODIC
        assert record.version == 1
        assert record.status == MemoryStatus.ACTIVE
        assert record.confidence == 0.5

    def test_default_values(self) -> None:
        now = time.time()
        record = MemoryRecord(
            memory_id="mem-002",
            memory_type=MemoryType.SEMANTIC,
            domain="geo",
            title="Title",
            content="Content",
            source="src",
            provenance="prov",
            created_at=now,
            updated_at=now,
        )
        assert record.evidence_refs == []
        assert record.entity_refs == []
        assert record.tags == []
        assert record.metadata == {}

    def test_generate_memory_id(self) -> None:
        id1 = generate_memory_id()
        id2 = generate_memory_id()
        assert id1.startswith("mem-")
        assert id1 != id2


class TestMemoryEnums:
    def test_memory_types(self) -> None:
        assert MemoryType.EPISODIC.value == "EPISODIC"
        assert MemoryType.SEMANTIC.value == "SEMANTIC"
        assert MemoryType.EVIDENCE.value == "EVIDENCE"
        assert MemoryType.WORKING.value == "WORKING"

    def test_memory_statuses(self) -> None:
        assert MemoryStatus.ACTIVE.value == "ACTIVE"
        assert MemoryStatus.ARCHIVED.value == "ARCHIVED"

    def test_relationship_types(self) -> None:
        assert RelationshipType.CONTRADICTS.value == "CONTRADICTS"
        assert RelationshipType.SUPPORTS.value == "SUPPORTS"
        assert RelationshipType.DERIVED_FROM.value == "DERIVED_FROM"


class TestWorkingMemory:
    def test_create_working(self) -> None:
        wm = WorkingMemory(session_id="ws-001", user_query="test query")
        assert wm.session_id == "ws-001"
        assert wm.user_query == "test query"
        assert wm.unresolved_questions == []
        assert wm.entities == []

    def test_add_entity(self) -> None:
        wm = WorkingMemory(session_id="ws-002")
        entity = EntityReference(
            entity_id="e-001",
            entity_type=EntityType.MARKET_ASSET,
            canonical_name="Test Asset",
        )
        wm.entities.append(entity)
        assert len(wm.entities) == 1
        assert wm.entities[0].entity_id == "e-001"


# ── Store Tests ────────────────────────────────────────────────────────────


class TestMemoryStore:
    def setup_method(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self.store = MemoryStore(self.tmp_dir)

    def teardown_method(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_create_and_get(self) -> None:
        record = self.store.create(
            MemoryRecord(
                memory_id="mem-001",
                memory_type=MemoryType.EPISODIC,
                domain="market",
                title="Test",
                content="Content",
                source="test",
                provenance="test:unit",
                created_at=1000.0,
                updated_at=1000.0,
            )
        )
        assert record.memory_id == "mem-001"
        fetched = self.store.get("mem-001")
        assert fetched is not None
        assert fetched.title == "Test"

    def test_create_duplicate(self) -> None:
        self.store.create(
            MemoryRecord(
                memory_id="mem-dup",
                memory_type=MemoryType.EPISODIC,
                domain="test",
                title="Dup",
                content="Dup content",
                source="test",
                provenance="test",
                created_at=1000.0,
                updated_at=1000.0,
            )
        )
        with pytest.raises(ValueError, match="already exists"):
            self.store.create(
                MemoryRecord(
                    memory_id="mem-dup",
                    memory_type=MemoryType.EPISODIC,
                    domain="test",
                    title="Dup2",
                    content="Dup2",
                    source="test",
                    provenance="test",
                    created_at=1000.0,
                    updated_at=1000.0,
                )
            )

    def test_update_creates_version(self) -> None:
        record = self.store.create(
            MemoryRecord(
                memory_id="mem-upd",
                memory_type=MemoryType.EPISODIC,
                domain="test",
                title="Original",
                content="Original content",
                source="test",
                provenance="test",
                created_at=1000.0,
                updated_at=1000.0,
            )
        )
        record.title = "Updated"
        record.version = 2
        updated = self.store.update(record)
        assert updated.title == "Updated"
        assert updated.version == 2
        versions = self.store.get_versions("mem-upd")
        assert len(versions) == 1

    def test_archive(self) -> None:
        self.store.create(
            MemoryRecord(
                memory_id="mem-arc",
                memory_type=MemoryType.EPISODIC,
                domain="test",
                title="Archive Me",
                content="To archive",
                source="test",
                provenance="test",
                created_at=1000.0,
                updated_at=1000.0,
            )
        )
        archived = self.store.archive("mem-arc")
        assert archived is not None
        assert archived.status == MemoryStatus.ARCHIVED

    def test_list_all(self) -> None:
        for i in range(5):
            self.store.create(
                MemoryRecord(
                    memory_id=f"mem-list-{i}",
                    memory_type=MemoryType.EPISODIC,
                    domain="test",
                    title=f"Item {i}",
                    content="Content",
                    source="test",
                    provenance="test",
                    created_at=1000.0 + i,
                    updated_at=1000.0 + i,
                )
            )
        records = self.store.list_all(limit=10)
        assert len(records) == 5

    def test_export(self) -> None:
        self.store.create(
            MemoryRecord(
                memory_id="mem-exp",
                memory_type=MemoryType.EPISODIC,
                domain="test",
                title="Export",
                content="Export content",
                source="test",
                provenance="test",
                created_at=1000.0,
                updated_at=1000.0,
            )
        )
        export_data = self.store.export_all()
        assert "records" in export_data
        assert len(export_data["records"]) == 1


# ── Index Tests ────────────────────────────────────────────────────────────


class TestMemoryIndex:
    def test_add_and_search(self) -> None:
        idx = MemoryIndex()
        record = MemoryRecord(
            memory_id="mem-idx-001",
            memory_type=MemoryType.EPISODIC,
            domain="market",
            title="Market Analysis Q4",
            content="Revenue growth analysis shows positive trend",
            source="test",
            provenance="test",
            created_at=1000.0,
            updated_at=1000.0,
        )
        idx.add(record)
        assert idx.size() == 1
        results = idx.search_tokens("market analysis")
        assert "mem-idx-001" in results

    def test_remove(self) -> None:
        idx = MemoryIndex()
        record = MemoryRecord(
            memory_id="mem-rm",
            memory_type=MemoryType.EPISODIC,
            domain="test",
            title="Remove Me",
            content="Content",
            source="test",
            provenance="test",
            created_at=1000.0,
            updated_at=1000.0,
        )
        idx.add(record)
        idx.remove("mem-rm")
        assert idx.size() == 0
        assert idx.search_tokens("remove") == set()

    def test_entity_index(self) -> None:
        idx = MemoryIndex()
        record = MemoryRecord(
            memory_id="mem-ent",
            memory_type=MemoryType.EVIDENCE,
            domain="geo",
            title="Satellite Observation",
            content="Observed change in NDVI",
            source="test",
            provenance="test",
            created_at=1000.0,
            updated_at=1000.0,
            entity_refs=["entity-abc", "entity-def"],
        )
        idx.add(record)
        results = idx.search_entities("entity-abc")
        assert "mem-ent" in results

    def test_domain_index(self) -> None:
        idx = MemoryIndex()
        record = MemoryRecord(
            memory_id="mem-dom",
            memory_type=MemoryType.SEMANTIC,
            domain="research",
            title="Research Finding",
            content="Finding content",
            source="test",
            provenance="test",
            created_at=1000.0,
            updated_at=1000.0,
        )
        idx.add(record)
        results = idx.search_domain("research")
        assert "mem-dom" in results

    def test_tag_index(self) -> None:
        idx = MemoryIndex()
        record = MemoryRecord(
            memory_id="mem-tag",
            memory_type=MemoryType.EPISODIC,
            domain="test",
            title="Tagged Memory",
            content="Content with tags",
            source="test",
            provenance="test",
            created_at=1000.0,
            updated_at=1000.0,
            tags=["important", "verified"],
        )
        idx.add(record)
        results = idx.search_tags("important")
        assert "mem-tag" in results


# ── Retrieval Tests ────────────────────────────────────────────────────────


class TestMemoryRetriever:
    def setup_method(self) -> None:
        self.index = MemoryIndex()
        self.retriever = MemoryRetriever(self.index)
        r1 = MemoryRecord(
            memory_id="mem-r1",
            memory_type=MemoryType.EPISODIC,
            domain="market",
            title="Market Analysis Q4 2025",
            content="Revenue growth analysis shows positive trend",
            source="test",
            provenance="test:q4",
            created_at=time.time() - 3600,
            updated_at=time.time() - 3600,
            status=MemoryStatus.ACTIVE,
            confidence=0.8,
        )
        r2 = MemoryRecord(
            memory_id="mem-r2",
            memory_type=MemoryType.EVIDENCE,
            domain="geo",
            title="Satellite Observation - NDVI",
            content="Vegetation index analysis from Sentinel-2",
            source="test",
            provenance="test:geo",
            created_at=time.time() - 7200,
            updated_at=time.time() - 7200,
            status=MemoryStatus.ACTIVE,
            confidence=0.6,
        )
        self.index.add(r1)
        self.index.add(r2)

    def test_search_by_query(self) -> None:
        results = self.retriever.retrieve(query="market analysis")
        assert len(results) > 0
        assert results[0].memory.memory_id == "mem-r1"
        assert results[0].score > 0

    def test_search_by_domain(self) -> None:
        results = self.retriever.retrieve(domain="geo")
        assert len(results) > 0
        assert results[0].memory.memory_id == "mem-r2"

    def test_search_by_entity(self) -> None:
        ent_record = MemoryRecord(
            memory_id="mem-ent-search",
            memory_type=MemoryType.EVIDENCE,
            domain="market",
            title="Entity Search Test",
            content="Content",
            source="test",
            provenance="test",
            created_at=time.time(),
            updated_at=time.time(),
            entity_refs=["entity-xyz"],
        )
        self.index.add(ent_record)
        results = self.retriever.retrieve(entity_id="entity-xyz")
        assert len(results) > 0
        assert results[0].memory.memory_id == "mem-ent-search"

    def test_excludes_archived(self) -> None:
        archived = MemoryRecord(
            memory_id="mem-archived",
            memory_type=MemoryType.EPISODIC,
            domain="test",
            title="Archived",
            content="Archived content",
            source="test",
            provenance="test",
            created_at=time.time(),
            updated_at=time.time(),
            status=MemoryStatus.ARCHIVED,
        )
        self.index.add(archived)
        results = self.retriever.retrieve(include_archived=False)
        assert all(r.memory.memory_id != "mem-archived" for r in results)

    def test_top_k_limit(self) -> None:
        results = self.retriever.retrieve(top_k=1)
        assert len(results) <= 1


# ── Relationship Tests ─────────────────────────────────────────────────────


class TestMemoryRelationships:
    def test_add_and_query(self) -> None:
        graph = MemoryRelationshipGraph()
        rel = MemoryRelationship(
            relationship_id="rel-001",
            source_id="mem-a",
            target_id="mem-b",
            relationship=RelationshipType.SUPPORTS,
            description="A supports B",
        )
        graph.add(rel)
        outgoing = graph.get_outgoing("mem-a")
        assert len(outgoing) == 1
        assert outgoing[0].target_id == "mem-b"

    def test_find_contradictions(self) -> None:
        graph = MemoryRelationshipGraph()
        graph.add(MemoryRelationship(
            relationship_id="rel-c1",
            source_id="mem-x",
            target_id="mem-y",
            relationship=RelationshipType.CONTRADICTS,
        ))
        graph.add(MemoryRelationship(
            relationship_id="rel-c2",
            source_id="mem-y",
            target_id="mem-x",
            relationship=RelationshipType.CONTRADICTS,
        ))
        contradictions = graph.find_contradictions()
        assert len(contradictions) == 1

    def test_get_chain(self) -> None:
        graph = MemoryRelationshipGraph()
        graph.add(MemoryRelationship(
            relationship_id="rel-ch1",
            source_id="mem-1",
            target_id="mem-2",
            relationship=RelationshipType.DERIVED_FROM,
        ))
        graph.add(MemoryRelationship(
            relationship_id="rel-ch2",
            source_id="mem-2",
            target_id="mem-3",
            relationship=RelationshipType.DERIVED_FROM,
        ))
        chain = graph.get_chain("mem-1", RelationshipType.DERIVED_FROM)
        assert "mem-1" in chain
        assert "mem-2" in chain
        assert "mem-3" in chain

    def test_remove(self) -> None:
        graph = MemoryRelationshipGraph()
        graph.add(MemoryRelationship(
            relationship_id="rel-rm",
            source_id="a",
            target_id="b",
            relationship=RelationshipType.SUPPORTS,
        ))
        assert graph.remove("rel-rm") is True
        assert len(graph.get_outgoing("a")) == 0

    def test_summary(self) -> None:
        graph = MemoryRelationshipGraph()
        graph.add(MemoryRelationship(
            relationship_id="rel-s1",
            source_id="a",
            target_id="b",
            relationship=RelationshipType.SUPPORTS,
        ))
        graph.add(MemoryRelationship(
            relationship_id="rel-s2",
            source_id="c",
            target_id="d",
            relationship=RelationshipType.CONTRADICTS,
        ))
        summary = graph.summary()
        assert "2 edges" in summary


# ── Manager Tests ──────────────────────────────────────────────────────────


class TestMemoryManager:
    def setup_method(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self.store = MemoryStore(self.tmp_dir)
        self.manager = MemoryManager(self.store)

    def teardown_method(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_create_and_get(self) -> None:
        record = self.manager.create(
            memory_type=MemoryType.EPISODIC,
            domain="market",
            title="Test Memory",
            content="Test content",
            source="test",
            provenance="test:unit",
        )
        assert record.memory_id.startswith("mem-")
        fetched = self.manager.get(record.memory_id)
        assert fetched is not None
        assert fetched.title == "Test Memory"

    def test_search(self) -> None:
        self.manager.create(
            memory_type=MemoryType.EPISODIC,
            domain="market",
            title="Revenue Analysis",
            content="Q4 revenue shows growth",
            source="test",
            provenance="test",
        )
        results = self.manager.search(query="revenue")
        assert len(results) > 0

    def test_link_and_get_relationships(self) -> None:
        r1 = self.manager.create(
            memory_type=MemoryType.EPISODIC,
            domain="test",
            title="Memory A",
            content="A",
            source="test",
            provenance="test",
        )
        r2 = self.manager.create(
            memory_type=MemoryType.EVIDENCE,
            domain="test",
            title="Memory B",
            content="B",
            source="test",
            provenance="test",
        )
        self.manager.link(r1.memory_id, r2.memory_id, RelationshipType.SUPPORTS, "A supports B")
        rels = self.manager.get_relationships(r1.memory_id)
        assert len(rels) == 1
        assert rels[0].relationship == RelationshipType.SUPPORTS

    def test_working_memory(self) -> None:
        wm = self.manager.start_session(query="test query", domain="market")
        assert wm.session_id.startswith("ws-")
        self.manager.update_working(unresolved_questions=["What is X?"])
        assert "What is X?" in self.manager.get_working().unresolved_questions

    def test_promote_working(self) -> None:
        self.manager.start_session(query="promote this", domain="test")
        self.manager.update_working(unresolved_questions=["Q1"])
        record = self.manager.promote_working()
        assert record is not None
        assert record.memory_type == MemoryType.EPISODIC

    def test_stats(self) -> None:
        self.manager.create(
            memory_type=MemoryType.EPISODIC,
            domain="market",
            title="Stats Test",
            content="Content",
            source="test",
            provenance="test",
        )
        stats = self.manager.stats()
        assert stats["total"] >= 1
        assert "by_type" in stats
        assert "by_domain" in stats

    def test_export(self) -> None:
        self.manager.create(
            memory_type=MemoryType.EPISODIC,
            domain="test",
            title="Export",
            content="Content",
            source="test",
            provenance="test",
        )
        data = self.manager.export()
        assert "records" in data
        assert len(data["records"]) >= 1

    def test_find_conflicts(self) -> None:
        r1 = self.manager.create(
            memory_type=MemoryType.EVIDENCE,
            domain="test",
            title="Claim A",
            content="A",
            source="test",
            provenance="test",
        )
        r2 = self.manager.create(
            memory_type=MemoryType.EVIDENCE,
            domain="test",
            title="Claim B",
            content="B",
            source="test",
            provenance="test",
        )
        self.manager.link(r1.memory_id, r2.memory_id, RelationshipType.CONTRADICTS)
        self.manager.link(r2.memory_id, r1.memory_id, RelationshipType.CONTRADICTS)
        conflicts = self.manager.find_conflicts()
        assert len(conflicts) == 1

    def test_retrieve_for_reasoning(self) -> None:
        self.manager.create(
            memory_type=MemoryType.SEMANTIC,
            domain="market",
            title="Market knowledge about equities",
            content="Equity analysis patterns and historical trends",
            source="test",
            provenance="test",
        )
        records = self.manager.retrieve_for_reasoning("market equities", domain="market")
        assert len(records) > 0

    def test_get_versions(self) -> None:
        record = self.manager.create(
            memory_type=MemoryType.EPISODIC,
            domain="test",
            title="Versioned",
            content="Original",
            source="test",
            provenance="test",
        )
        record.title = "Updated"
        record.version = 2
        self.manager.update(record, change_reason="Title fix")
        versions = self.manager.get_versions(record.memory_id)
        assert len(versions) == 1
