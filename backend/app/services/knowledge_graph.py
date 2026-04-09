"""Knowledge graph service — builds and queries a graph from payer policy data."""

from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.database import KGEdge, KGNode, PayerPolicy

# ---------------------------------------------------------------------------
# ICD-10 → human-readable diagnosis label
# ---------------------------------------------------------------------------

ICD10_LABELS: dict[str, str] = {
    "M17.11": "Primary osteoarthritis, right knee",
    "M17.12": "Primary osteoarthritis, left knee",
    "M16.11": "Primary osteoarthritis, right hip",
    "M16.12": "Primary osteoarthritis, left hip",
    "M75.11": "Rotator cuff tear, right shoulder",
    "M75.12": "Rotator cuff tear, left shoulder",
    "M54.5": "Low back pain",
    "M47.816": "Spondylosis with myelopathy, lumbar",
    "M51.16": "Lumbar disc disorder with radiculopathy",
    "M48.06": "Spinal stenosis, lumbar",
    "G89.29": "Other chronic pain",
    "G89.4": "Chronic pain syndrome",
}

# Prefix-based fallback: "M17" → knee OA labels, etc.
_ICD10_PREFIX_TO_LABELS: dict[str, list[str]] = {
    "M17": ["Primary osteoarthritis, right knee", "Primary osteoarthritis, left knee"],
    "M16": ["Primary osteoarthritis, right hip", "Primary osteoarthritis, left hip"],
    "M75": ["Rotator cuff tear, right shoulder", "Rotator cuff tear, left shoulder"],
    "M54": ["Low back pain"],
    "M47": ["Spondylosis with myelopathy, lumbar"],
    "M51": ["Lumbar disc disorder with radiculopathy"],
    "M48": ["Spinal stenosis, lumbar"],
    "G89": ["Other chronic pain", "Chronic pain syndrome"],
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_diagnosis_labels(icd_codes: list[str]) -> list[str]:
    """Return human-readable labels for a list of ICD-10 codes.

    Falls back to prefix matching when the exact code is not in ICD10_LABELS.
    """
    labels: list[str] = []
    seen: set[str] = set()

    for code in icd_codes:
        code = code.strip()
        if not code:
            continue

        if code in ICD10_LABELS:
            lbl = ICD10_LABELS[code]
            if lbl not in seen:
                labels.append(lbl)
                seen.add(lbl)
            continue

        # Try prefix (first 3-4 chars)
        matched = False
        for prefix, prefix_labels in _ICD10_PREFIX_TO_LABELS.items():
            if code.startswith(prefix):
                for lbl in prefix_labels:
                    if lbl not in seen:
                        labels.append(lbl)
                        seen.add(lbl)
                matched = True
                break

        if not matched:
            # Keep the raw code as a label so we don't silently drop it
            lbl = f"Diagnosis {code}"
            if lbl not in seen:
                labels.append(lbl)
                seen.add(lbl)

    return labels


async def _get_or_create_node(
    db: AsyncSession,
    node_cache: dict[tuple[str, str], KGNode],
    node_type: str,
    label: str,
    properties: dict | None = None,
) -> tuple[KGNode, bool]:
    """Return (node, created).  Checks the in-memory cache first, then the DB."""
    key = (node_type, label)
    if key in node_cache:
        return node_cache[key], False

    result = await db.execute(
        select(KGNode)
        .where(KGNode.node_type == node_type)
        .where(KGNode.label == label)
        .limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing:
        node_cache[key] = existing
        return existing, False

    node = KGNode(node_type=node_type, label=label, properties=properties or {})
    db.add(node)
    await db.flush()  # populate node.id without a full commit
    node_cache[key] = node
    return node, True


async def _get_or_create_edge(
    db: AsyncSession,
    edge_cache: set[tuple],
    source_node_id,
    target_node_id,
    edge_type: str,
    properties: dict | None = None,
    confidence: float = 1.0,
    source_chunk_id=None,
) -> tuple[KGEdge, bool]:
    """Return (edge, created).  Deduplicates by (source, target, type)."""
    key = (source_node_id, target_node_id, edge_type)
    if key in edge_cache:
        return None, False  # type: ignore[return-value]

    edge_cache.add(key)
    edge = KGEdge(
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        edge_type=edge_type,
        properties=properties or {},
        confidence=confidence,
        source_chunk_id=source_chunk_id,
    )
    db.add(edge)
    return edge, True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def build_graph_from_policies(db: AsyncSession) -> dict:
    """Read all active PayerPolicy records and (re-)build the knowledge graph.

    Clears the existing graph first (edges before nodes to respect FK constraints),
    then creates:
      - payer node
      - procedure node
      - criterion nodes (one per distinct requirement)
      - treatment nodes (one per required modality)
      - diagnosis nodes (from ICD-10 codes in the policy criteria)

    Edges created:
      - procedure  --offered_by-->  payer
      - procedure  --requires-->    criterion
      - treatment  --modality_of--> criterion  (for conservative-treatment criteria)
      - procedure  --treats-->      diagnosis

    Returns {"nodes_created": N, "edges_created": N}.
    """
    logger.info("build_graph_from_policies: clearing existing graph")

    await db.execute(delete(KGEdge))
    await db.execute(delete(KGNode))
    await db.flush()

    # Fetch all active policies
    result = await db.execute(
        select(PayerPolicy).where(PayerPolicy.status == "active")
    )
    policies: list[PayerPolicy] = list(result.scalars().all())
    logger.info("build_graph_from_policies: processing %d active policies", len(policies))

    node_cache: dict[tuple[str, str], KGNode] = {}
    edge_cache: set[tuple] = set()
    nodes_created = 0
    edges_created = 0

    for policy in policies:
        criteria: dict = policy.criteria or {}

        # --- payer node ---
        payer_node, created = await _get_or_create_node(
            db, node_cache, "payer", policy.payer,
            properties={"name": policy.payer},
        )
        if created:
            nodes_created += 1

        # --- procedure node ---
        proc_node, created = await _get_or_create_node(
            db, node_cache, "procedure", policy.procedure,
            properties={"name": policy.procedure},
        )
        if created:
            nodes_created += 1

        # Edge: procedure --offered_by--> payer
        _, edge_created = await _get_or_create_edge(
            db, edge_cache,
            proc_node.id, payer_node.id, "offered_by",
        )
        if edge_created:
            edges_created += 1

        # --- conservative treatment criterion ---
        min_months = criteria.get("conservative_treatment_min_months")
        modalities: list[str] = criteria.get("required_modalities", [])

        if min_months is not None or modalities:
            months_str = f" \u2265 {min_months} months" if min_months else ""
            criterion_label = f"Conservative Treatment{months_str}"

            criterion_node, created = await _get_or_create_node(
                db, node_cache, "criterion", criterion_label,
                properties={
                    "min_months": min_months,
                    "modalities": modalities,
                },
            )
            if created:
                nodes_created += 1

            # Edge: procedure --requires--> criterion
            _, edge_created = await _get_or_create_edge(
                db, edge_cache,
                proc_node.id, criterion_node.id, "requires",
                properties={"criterion_type": "conservative_treatment"},
            )
            if edge_created:
                edges_created += 1

            # treatment nodes + modality_of edges
            for modality in modalities:
                treatment_node, created = await _get_or_create_node(
                    db, node_cache, "treatment", modality,
                    properties={"modality": modality},
                )
                if created:
                    nodes_created += 1

                _, edge_created = await _get_or_create_edge(
                    db, edge_cache,
                    treatment_node.id, criterion_node.id, "modality_of",
                )
                if edge_created:
                    edges_created += 1

        # --- imaging criterion ---
        imaging_required = criteria.get("imaging_required")
        if imaging_required:
            criterion_label = imaging_required
            criterion_node, created = await _get_or_create_node(
                db, node_cache, "criterion", criterion_label,
                properties={"criterion_type": "imaging"},
            )
            if created:
                nodes_created += 1

            _, edge_created = await _get_or_create_edge(
                db, edge_cache,
                proc_node.id, criterion_node.id, "requires",
                properties={"criterion_type": "imaging"},
            )
            if edge_created:
                edges_created += 1

        # --- trial criterion (e.g. SCS trial required) ---
        if criteria.get("trial_required"):
            criterion_label = f"{policy.procedure} Trial Required"
            criterion_node, created = await _get_or_create_node(
                db, node_cache, "criterion", criterion_label,
                properties={"criterion_type": "trial"},
            )
            if created:
                nodes_created += 1

            _, edge_created = await _get_or_create_edge(
                db, edge_cache,
                proc_node.id, criterion_node.id, "requires",
                properties={"criterion_type": "trial"},
            )
            if edge_created:
                edges_created += 1

        # --- generic requirement nodes from remaining criteria keys ---
        skip_keys = {
            "conservative_treatment_min_months",
            "required_modalities",
            "imaging_required",
            "trial_required",
            "submission_portal",
        }
        for key, value in criteria.items():
            if key in skip_keys or value is None or value == "" or value is False:
                continue
            # Represent as a requirement node on the payer
            req_label = f"{policy.payer}: {key.replace('_', ' ').title()}"
            req_node, created = await _get_or_create_node(
                db, node_cache, "requirement", req_label,
                properties={"key": key, "value": value, "payer": policy.payer},
            )
            if created:
                nodes_created += 1

            _, edge_created = await _get_or_create_edge(
                db, edge_cache,
                payer_node.id, req_node.id, "has_requirement",
                properties={"procedure": policy.procedure},
            )
            if edge_created:
                edges_created += 1

        # --- diagnosis nodes ---
        icd_codes: list[str] = criteria.get("icd_codes", [])
        # Also check top-level diagnosis_code field stored directly on criteria
        raw_diag = criteria.get("diagnosis_code")
        if raw_diag and isinstance(raw_diag, str):
            icd_codes = list({raw_diag, *icd_codes})

        diagnosis_labels = _resolve_diagnosis_labels(icd_codes)

        for diag_label in diagnosis_labels:
            diag_node, created = await _get_or_create_node(
                db, node_cache, "diagnosis", diag_label,
                properties={"source": "icd10"},
            )
            if created:
                nodes_created += 1

            _, edge_created = await _get_or_create_edge(
                db, edge_cache,
                proc_node.id, diag_node.id, "treats",
            )
            if edge_created:
                edges_created += 1

    await db.commit()

    logger.info(
        "build_graph_from_policies: done — nodes_created=%d edges_created=%d",
        nodes_created,
        edges_created,
    )
    return {"nodes_created": nodes_created, "edges_created": edges_created}


async def get_related_requirements(
    db: AsyncSession,
    payer: str,
    procedure: str,
) -> list[dict]:
    """Traverse the graph to find all requirements for a payer+procedure combo.

    Walk path: payer_node <--offered_by-- procedure_node --requires--> criterion_node
    Also follows criterion_node <--modality_of-- treatment_node to attach modalities.

    Returns a list of:
        {"requirement": str, "criterion_type": str, "details": dict}
    """
    # 1. Locate the procedure node
    result = await db.execute(
        select(KGNode)
        .where(KGNode.node_type == "procedure")
        .where(KGNode.label == procedure)
        .limit(1)
    )
    proc_node = result.scalar_one_or_none()
    if not proc_node:
        logger.warning(
            "get_related_requirements: no procedure node found for '%s'", procedure
        )
        return []

    # 2. Confirm an offered_by edge connects this procedure to the requested payer
    result = await db.execute(
        select(KGNode)
        .join(KGEdge, KGEdge.target_node_id == KGNode.id)
        .where(KGEdge.source_node_id == proc_node.id)
        .where(KGEdge.edge_type == "offered_by")
        .where(KGNode.node_type == "payer")
        .where(KGNode.label == payer)
        .limit(1)
    )
    payer_node = result.scalar_one_or_none()
    if not payer_node:
        logger.warning(
            "get_related_requirements: no payer node '%s' linked to procedure '%s'",
            payer,
            procedure,
        )
        return []

    # 3. Fetch all criterion nodes the procedure requires
    result = await db.execute(
        select(KGNode, KGEdge)
        .join(KGEdge, KGEdge.target_node_id == KGNode.id)
        .where(KGEdge.source_node_id == proc_node.id)
        .where(KGEdge.edge_type == "requires")
        .where(KGNode.node_type == "criterion")
    )
    rows = result.all()

    requirements: list[dict] = []
    for criterion_node, edge in rows:
        criterion_type = (edge.properties or {}).get("criterion_type", "general")
        details: dict = dict(criterion_node.properties or {})

        # 4. Attach treatment modalities that feed this criterion
        mod_result = await db.execute(
            select(KGNode)
            .join(KGEdge, KGEdge.source_node_id == KGNode.id)
            .where(KGEdge.target_node_id == criterion_node.id)
            .where(KGEdge.edge_type == "modality_of")
            .where(KGNode.node_type == "treatment")
        )
        modality_nodes = mod_result.scalars().all()
        if modality_nodes:
            details["modalities"] = [n.label for n in modality_nodes]

        requirements.append(
            {
                "requirement": criterion_node.label,
                "criterion_type": criterion_type,
                "details": details,
            }
        )

    logger.info(
        "get_related_requirements: payer=%s procedure=%s → %d requirements",
        payer,
        procedure,
        len(requirements),
    )
    return requirements


async def find_cross_payer_insights(
    db: AsyncSession,
    procedure: str,
    diagnosis_code: str | None = None,
) -> list[dict]:
    """Cross-payer intelligence for a given procedure (and optionally a diagnosis).

    Returns a list of insight dicts with keys:
      - "insight_type": "common_requirement" | "unique_requirement" | "related_diagnosis"
      - "label": human-readable description
      - "payers": list of payer names that share this requirement (for common/unique)
      - "details": dict with extra metadata
    """
    # ------------------------------------------------------------------
    # 1. Locate the procedure node
    # ------------------------------------------------------------------
    result = await db.execute(
        select(KGNode)
        .where(KGNode.node_type == "procedure")
        .where(KGNode.label == procedure)
        .limit(1)
    )
    proc_node = result.scalar_one_or_none()
    if not proc_node:
        logger.warning(
            "find_cross_payer_insights: no procedure node found for '%s'", procedure
        )
        return []

    # ------------------------------------------------------------------
    # 2. Which payers offer this procedure?
    # ------------------------------------------------------------------
    result = await db.execute(
        select(KGNode)
        .join(KGEdge, KGEdge.target_node_id == KGNode.id)
        .where(KGEdge.source_node_id == proc_node.id)
        .where(KGEdge.edge_type == "offered_by")
        .where(KGNode.node_type == "payer")
    )
    all_payer_nodes = result.scalars().all()
    all_payer_names = {n.label for n in all_payer_nodes}

    if not all_payer_names:
        logger.warning(
            "find_cross_payer_insights: procedure '%s' has no payer links", procedure
        )
        return []

    # ------------------------------------------------------------------
    # 3. Gather all criteria this procedure requires, indexed by criterion label
    #    Each criterion may be linked to multiple payers through separate
    #    PayerPolicy rows — but our graph collapses shared labels.
    #    We rebuild the per-criterion payer set by checking which payer policies
    #    share the same procedure+criterion pair in the DB.
    # ------------------------------------------------------------------

    # Fetch all (criterion_node, edge) pairs for this procedure
    result = await db.execute(
        select(KGNode, KGEdge)
        .join(KGEdge, KGEdge.target_node_id == KGNode.id)
        .where(KGEdge.source_node_id == proc_node.id)
        .where(KGEdge.edge_type == "requires")
        .where(KGNode.node_type == "criterion")
    )
    criterion_rows = result.all()

    # Map: criterion_label → {payers} (rebuilt from PayerPolicy source)
    # We approximate payer coverage using the criteria.properties where possible,
    # but since the graph uses get_or_create, a shared criterion node doesn't
    # record which payers require it.  We therefore cross-reference the
    # payer_policies table directly.
    criterion_to_payers: dict[str, set[str]] = defaultdict(set)

    all_policies_result = await db.execute(
        select(PayerPolicy)
        .where(PayerPolicy.status == "active")
        .where(PayerPolicy.procedure == procedure)
    )
    procedure_policies: list[PayerPolicy] = list(all_policies_result.scalars().all())

    # Build a quick map: payer → set of criterion labels it imposes
    payer_to_criteria: dict[str, set[str]] = defaultdict(set)
    for policy in procedure_policies:
        crit = policy.criteria or {}
        min_months = crit.get("conservative_treatment_min_months")
        modalities = crit.get("required_modalities", [])
        if min_months is not None or modalities:
            months_str = f" \u2265 {min_months} months" if min_months else ""
            payer_to_criteria[policy.payer].add(f"Conservative Treatment{months_str}")
        if crit.get("imaging_required"):
            payer_to_criteria[policy.payer].add(crit["imaging_required"])
        if crit.get("trial_required"):
            payer_to_criteria[policy.payer].add(f"{policy.procedure} Trial Required")

    # Invert: criterion_label → payers
    for payer_name, labels in payer_to_criteria.items():
        for lbl in labels:
            criterion_to_payers[lbl].add(payer_name)

    # For criterion nodes that don't appear in any payer_to_criteria mapping
    # (e.g. they were created from fields we didn't enumerate above),
    # fall back: assume all payers in all_payer_names require it.
    criterion_node_map: dict[str, KGNode] = {}
    for criterion_node, edge in criterion_rows:
        criterion_node_map[criterion_node.label] = criterion_node
        if criterion_node.label not in criterion_to_payers:
            criterion_to_payers[criterion_node.label] = set(all_payer_names)

    # ------------------------------------------------------------------
    # 4. Classify: common (all payers) vs. unique (exactly one payer)
    # ------------------------------------------------------------------
    insights: list[dict] = []
    total_payers = len(all_payer_names)

    for criterion_label, payers in criterion_to_payers.items():
        node = criterion_node_map.get(criterion_label)
        details: dict = dict(node.properties or {}) if node else {}

        # Attach modalities if present
        if node:
            mod_result = await db.execute(
                select(KGNode)
                .join(KGEdge, KGEdge.source_node_id == KGNode.id)
                .where(KGEdge.target_node_id == node.id)
                .where(KGEdge.edge_type == "modality_of")
                .where(KGNode.node_type == "treatment")
            )
            modality_nodes = mod_result.scalars().all()
            if modality_nodes:
                details["modalities"] = [n.label for n in modality_nodes]

        payer_list = sorted(payers)
        if len(payers) == total_payers:
            insights.append(
                {
                    "insight_type": "common_requirement",
                    "label": criterion_label,
                    "payers": payer_list,
                    "details": {
                        **details,
                        "note": "Required by all payers covering this procedure",
                    },
                }
            )
        elif len(payers) == 1:
            insights.append(
                {
                    "insight_type": "unique_requirement",
                    "label": criterion_label,
                    "payers": payer_list,
                    "details": {
                        **details,
                        "note": f"Unique to {payer_list[0]}",
                    },
                }
            )
        else:
            # Majority / minority requirement — still useful
            insights.append(
                {
                    "insight_type": "shared_requirement",
                    "label": criterion_label,
                    "payers": payer_list,
                    "details": {
                        **details,
                        "note": f"Required by {len(payers)} of {total_payers} payers",
                    },
                }
            )

    # ------------------------------------------------------------------
    # 5. Related diagnoses — what diagnoses does this procedure treat?
    #    Optionally cross-reference against other procedures that treat
    #    the same diagnosis if diagnosis_code is supplied.
    # ------------------------------------------------------------------
    diag_result = await db.execute(
        select(KGNode)
        .join(KGEdge, KGEdge.target_node_id == KGNode.id)
        .where(KGEdge.source_node_id == proc_node.id)
        .where(KGEdge.edge_type == "treats")
        .where(KGNode.node_type == "diagnosis")
    )
    diag_nodes = diag_result.scalars().all()

    # Target diagnoses — either all, or filtered to the supplied code's label
    target_diag_labels: set[str] = {n.label for n in diag_nodes}

    if diagnosis_code:
        specific_labels = _resolve_diagnosis_labels([diagnosis_code])
        if specific_labels:
            target_diag_labels &= set(specific_labels)

    for diag_node in diag_nodes:
        if diag_node.label not in target_diag_labels:
            continue

        # Find other procedures that also treat this diagnosis
        other_proc_result = await db.execute(
            select(KGNode)
            .join(KGEdge, KGEdge.source_node_id == KGNode.id)
            .where(KGEdge.target_node_id == diag_node.id)
            .where(KGEdge.edge_type == "treats")
            .where(KGNode.node_type == "procedure")
            .where(KGNode.id != proc_node.id)
        )
        other_procs = other_proc_result.scalars().all()

        insights.append(
            {
                "insight_type": "related_diagnosis",
                "label": diag_node.label,
                "payers": sorted(all_payer_names),
                "details": {
                    "diagnosis": diag_node.label,
                    "also_treated_by": [p.label for p in other_procs],
                    "note": (
                        f"Treated by {procedure}"
                        + (
                            f" and {len(other_procs)} other procedure(s)"
                            if other_procs
                            else ""
                        )
                    ),
                },
            }
        )

    logger.info(
        "find_cross_payer_insights: procedure=%s diagnosis_code=%s → %d insights",
        procedure,
        diagnosis_code,
        len(insights),
    )
    return insights
