"""FastAPI wrapper exposing gui3.py backend features (upload, chat, diagnosis).

This API surfaces three main capabilities formerly tied to the Tkinter UI:
1) Circuit file upload (.cir + .log) → Supabase ingest + optional .meas block helper
2) Chat assistant backed by lab-manual retrieval and LLM
3) Circuit debugger that runs the LLM-based diagnosis on a selected circuit

Run locally with:
    uvicorn api:app --reload --host 0.0.0.0 --port 8000

Required deps (pip): fastapi, uvicorn, python-dotenv, supabase, langchain-ollama
"""

import math
import os
import re
import tempfile
import textwrap
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, Depends
from pydantic import BaseModel
from supabase import Client, create_client
from langchain_ollama import OllamaLLM, OllamaEmbeddings

from open_webui.models.files import Files
from open_webui.storage.provider import Storage
from open_webui.utils.auth import get_verified_user

# ==========================================
# 1. SETUP & GLOBAL CONFIGURATION
# ==========================================

load_dotenv()
SUPABASE_URL = "https://mvyumvpmzcrrcwcppcea.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im12eXVtdnBtemNycmN3Y3BwY2VhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjE2Njk2MDQsImV4cCI6MjA3NzI0NTYwNH0.WfjqQowIt9lxKPdnWSGEOP_u7MKmetWgIPFOASuzeBw"

supabase: Optional[Client] = None
llm: Optional[OllamaLLM] = None
embedder: Optional[OllamaEmbeddings] = None
conversation_history: List[Dict[str, str]] = []

CONTEXT_MATCH_THRESHOLD = float(os.getenv("LAB_MATCH_THRESHOLD", "0.58"))
SECOND_PASS_THRESHOLD = float(os.getenv("LAB_SECOND_PASS_THRESHOLD", "0.48"))
CONTEXT_MATCH_COUNT = int(os.getenv("LAB_MATCH_COUNT", "30"))
CONTEXT_FINAL_K = int(os.getenv("LAB_FINAL_K", "10"))
CONTEXT_SECTION_LIMIT = int(os.getenv("LAB_SECTION_LIMIT", "4"))
CONTEXT_SCORE_TOLERANCE = float(os.getenv("LAB_SCORE_TOLERANCE", "0.08"))
CONTEXT_MAX_CHARS = int(os.getenv("LAB_CONTEXT_MAX_CHARS", "1800"))
MANUAL_VERSION = os.getenv("LAB_MANUAL_VERSION")
BM25_K1 = float(os.getenv("LAB_BM25_K1", "1.2"))
BM25_B = float(os.getenv("LAB_BM25_B", "0.75"))
USE_LLM_RERANK = os.getenv("LAB_USE_LLM_RERANK", "false").lower() == "true"
RERANK_TOP = int(os.getenv("LAB_RERANK_TOP", "15"))
RERANK_KEEP = int(os.getenv("LAB_RERANK_KEEP", "8"))

try:
    if SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        llm = OllamaLLM(
            model=os.getenv("LAB_LLM_MODEL", "gpt-oss:120b-cloud"),
            temperature=float(os.getenv("LAB_TEMPERATURE", "0")),
        )
        embedder = OllamaEmbeddings(model="mxbai-embed-large")
    else:
        print("WARNING: SUPABASE_KEY missing; API will return 503 for DB routes.")
except Exception as e:  # pragma: no cover - startup diagnostics only
    print(f"Startup Error: {e}")


# ==========================================
# 2. BACKEND HELPERS (from gui3.py without GUI deps)
# ==========================================


def get_latest_circuit() -> Optional[Dict]:
    res = supabase.table("spice_files").select("*").order("created_at", desc=True).limit(1).execute()
    return res.data[0] if res.data else None


def get_nodes_and_elements(spice_id: str) -> Tuple[List[Dict], List[Dict]]:
    nodes_res = supabase.table("spice_nets").select("*").eq("spice_id", spice_id).execute()
    elems_res = supabase.table("spice_elements").select("*").eq("spice_id", spice_id).not_.is_("simulated_current", "null").execute()
    return nodes_res.data or [], elems_res.data or []


def insert_data_to_supabase(cir_path: str, merged_data: List[Dict], volts_data: Dict) -> str:
    try:
        circuit_name = os.path.basename(cir_path)  # works for paths OR plain filenames
        file_res = supabase.table("spice_files").insert({"circuit_name": circuit_name}).execute()
        spice_id = file_res.data[0]["id"]

        nets_payload = [{"spice_id": spice_id, "node_name": k, "simulated_voltage": v} for k, v in volts_data.items()]
        if nets_payload:
            supabase.table("spice_nets").insert(nets_payload).execute()

        elems_payload = []
        for e in merged_data:
            elems_payload.append({
                "spice_id": spice_id,
                "element_name": e["name"],
                "type": e["type"],
                "model": e["model"],
                "value": e["value"],
                "parameters": e["params"],
                "simulated_current": e["simulated_current"],
            })
        if elems_payload:
            e_res = supabase.table("spice_elements").insert(elems_payload).execute()
            name_to_id = {el["element_name"]: el["id"] for el in e_res.data}
            conns = []
            for e in merged_data:
                uid = name_to_id.get(e["name"])
                if uid:
                    for i, node in enumerate(e["nodes"]):
                        conns.append({"element_id": uid, "node_name": node, "node_order": i})
            if conns:
                supabase.table("element_connections").insert(conns).execute()

        return f"Success! Uploaded ID: {spice_id}"
    except Exception as e:  # pragma: no cover - direct DB interaction
        return f"Error: {str(e)}"


def read_text_auto(filepath: str) -> str:
    data = Path(filepath).read_bytes()

    if b"\x00" in data:
        if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
            try:
                return data.decode("utf-16")
            except UnicodeError:
                pass
        for enc in ("utf-16-le", "utf-16-be"):
            try:
                return data.decode(enc)
            except UnicodeError:
                continue

    try:
        return data.decode("utf-8")
    except UnicodeError:
        return ""


def parse_cir_lines(path: str) -> List[Dict]:
    text = read_text_auto(path)
    elements = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("*"):
            continue
        parts = line.split()
        if parts[0][0].upper() not in ["R", "C", "V", "I", "X", "D"]:
            continue
        name, type_ = parts[0], parts[0][0].upper()
        nodes, model, value, params = [], None, None, {}
        if type_ == "X":
            eq_idx = next((i for i, t in enumerate(parts) if "=" in t), None)
            node_tokens = parts[1:eq_idx] if eq_idx else parts[1:]
            if node_tokens:
                *nodes, model = node_tokens
        else:
            if len(parts) >= 4:
                name, nodes, value = parts[0], parts[1:3], parts[3]
        elements.append({
            "name": name,
            "type": type_,
            "nodes": nodes,
            "model": model,
            "value": value,
            "params": params,
            "simulated_current": None,
            "node_voltages": {n: None for n in nodes},
        })
    return elements


def parse_log_file(path: str) -> Tuple[Dict, Dict, Dict]:
    text = read_text_auto(path).replace("\x00", "").replace("\xa0", " ")
    text = re.sub(r"[ ]{2,}", " ", text)
    v = {m.group(1).upper(): float(m.group(2)) for m in re.finditer(r"V\(([^)]+)\)\s+([-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?)", text, re.I)}
    i = {m.group(1).upper(): float(m.group(2)) for m in re.finditer(r"I\(([^)]+)\)\s+([-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?)", text, re.I)}
    if "0" not in v:
        v["0"] = 0.0
    return v, i, {}


def merge_simulation_data(elems: List[Dict], v: Dict, i: Dict, sub: Dict) -> List[Dict]:
    for e in elems:
        if e["name"].upper() in i:
            e["simulated_current"] = i[e["name"].upper()]
        for n in e["node_voltages"]:
            if n.upper() in v:
                e["node_voltages"][n] = v[n.upper()]
    return elems


def generate_meas_block(nodes: List[Dict]) -> str:
    output = []
    output.append("* -----------------------------------------------------------")
    output.append("* AUTO-GENERATED MEASUREMENT COMMANDS")
    output.append("* Copy and paste these into your LTspice Transient Simulation")
    output.append("* Note: Frequency/Period triggers assume a 0V crossing.")
    output.append("* -----------------------------------------------------------")

    for node in nodes:
        n = node["node_name"]
        output.append(f"\n* Measurements for Node {n}")
        output.append(f".meas TRAN avg_{n} AVG V({n})")
        output.append(f".meas TRAN max_{n} MAX V({n})")
        output.append(f".meas TRAN min_{n} MIN V({n})")
        output.append(f".meas TRAN pp_{n} PP V({n})")
        output.append(f".meas TRAN rms_{n} RMS V({n})")
        output.append(f".meas TRAN period_{n} TRIG V({n})=0 RISE=1 TARG V({n})=0 RISE=2")
        output.append(f".meas TRAN freq_{n} PARAM 1/period_{n}")

    return "\n".join(output)


def fetch_spice_rows(spice_id: str) -> Tuple[List[Dict], List[Dict]]:
    nets_res = supabase.table("spice_nets").select("*").eq("spice_id", spice_id).execute()
    nets = nets_res.data if nets_res.data else []

    elems_res = supabase.table("spice_elements").select("*").eq("spice_id", spice_id).not_.is_("simulated_current", "null").execute()
    elems_raw = elems_res.data if elems_res.data else []

    elem_ids = [e["id"] for e in elems_raw] if elems_raw else []
    connections = []
    if elem_ids:
        conn_res = supabase.table("element_connections").select("element_id, node_name, node_order").in_("element_id", elem_ids).execute()
        connections = conn_res.data if conn_res.data else []

    node_map = {}
    for c in connections:
        eid = c["element_id"]
        node_map.setdefault(eid, []).append((c["node_order"], c["node_name"]))

    elements = []
    for e in elems_raw:
        nodes = sorted(node_map.get(e["id"], []), key=lambda x: x[0])
        e_updated = dict(e)
        e_updated["node_pos"] = nodes[0][1] if len(nodes) >= 1 else None
        e_updated["node_neg"] = nodes[1][1] if len(nodes) >= 2 else None
        elements.append(e_updated)

    normalized_nets = []
    gnd_sim, gnd_meas = None, None
    for n in nets:
        up = str(n.get("node_name")).upper()
        if up in ("0", "GND", "GROUND"):
            gnd_sim = n.get("simulated_voltage") or n.get("simulated_avg")
            gnd_meas = n.get("measured_voltage") or n.get("measured_avg")
        else:
            normalized_nets.append(n)

    normalized_nets.append({
        "node_name": "0",
        "simulated_voltage": gnd_sim or 0.0,
        "measured_voltage": gnd_meas or 0.0,
        "simulated_avg": gnd_sim or 0.0,
        "measured_avg": gnd_meas or 0.0,
    })
    return normalized_nets, elements


def build_diagnosis_prompt(circuit_name: str, nets: List[Dict], elems: List[Dict]) -> str:
    def fmt(val, unit=""):
        if val is None:
            return "N/A"
        try:
            f = float(val)
            if abs(f) < 0.001 and f != 0:
                return f"{f:.4e}{unit}"
            return f"{f:.4f}{unit}"
        except Exception:
            return "N/A"

    node_lines = []
    for n in sorted(nets, key=lambda x: str(x.get("node_name", ""))):
        details = []
        sim_avg = n.get("simulated_avg") if n.get("simulated_avg") is not None else n.get("simulated_voltage")
        meas_avg = n.get("measured_avg") if n.get("measured_avg") is not None else n.get("measured_voltage")
        details.append(f"   - Avg Voltage:   Sim={fmt(sim_avg, 'V')} vs Meas={fmt(meas_avg, 'V')}")

        s_pp, m_pp = n.get("simulated_pp"), n.get("measured_pp")
        if (s_pp and float(s_pp) > 0) or (m_pp and float(m_pp) > 0):
            details.append(f"   - P-P:      Sim={fmt(s_pp, 'V')} vs Meas={fmt(m_pp, 'V')}")

        s_rms, m_rms = n.get("simulated_rms"), n.get("measured_rms")
        if (s_rms and float(s_rms) > 0) or (m_rms and float(m_rms) > 0):
            details.append(f"   - RMS:      Sim={fmt(s_rms, 'V')} vs Meas={fmt(m_rms, 'V')}")

        s_freq, m_freq = n.get("simulated_freq"), n.get("measured_freq")
        if s_freq or m_freq:
            details.append(f"   - Freq:     Sim={fmt(s_freq, 'Hz')} vs Meas={fmt(m_freq, 'Hz')}")

        s_max, s_min = n.get("simulated_max"), n.get("simulated_min")
        m_max, m_min = n.get("measured_max"), n.get("measured_min")
        if (s_max is not None) or (m_max is not None):
            sim_range = f"[{fmt(s_max)}, {fmt(s_min)}]" if s_max is not None else "N/A"
            meas_range = f"[{fmt(m_max)}, {fmt(m_min)}]" if m_max is not None else "N/A"
            details.append(f"   - Range:    Sim={sim_range} vs Meas={meas_range}")

        node_block = f"Node {n.get('node_name')}:\n" + "\n".join(details)
        node_lines.append(node_block)

    node_text = "\n\n".join(node_lines)

    elem_lines = []
    for e in elems:
        if e.get("type") == "X":
            node_str = "See Schematic (Multi-pin)"
        else:
            node_str = f"({e.get('node_pos')} -> {e.get('node_neg')})"
        sim_i = e.get("simulated_current")
        meas_i = e.get("measured_current")
        elem_lines.append(f"- {e.get('element_name')} {node_str}: Sim={fmt(sim_i, 'A')} vs Meas={fmt(meas_i, 'A')}")

    elem_text = "\n".join(elem_lines)

    instruction_template = """
    ======================================
    TASK (OPTIMIZED FOR BREADBOARD DEBUGGING)
    ======================================
    Using ONLY the data above, identify the SINGLE most likely real-world breadboard wiring/component error. Restrict your reasoning strictly to mistakes physically possible on a breadboard. Always respond in English

    When reasoning, you MUST use the following checklist:

    1. **Op-Amp Saturation (Swapped Inputs)**
       - **Symptom:** Simulated voltage is ~0V or very low, but Measured voltage is stuck near a supply rail (e.g., +4V on 5V supply, or +13V on 15V supply).
       - **Diagnosis:** "Swapped Op-Amp Inputs (+/-)".
       - **Reasoning:** This creates Positive Feedback, forcing the output to latch to the rail.

    2. **Continuity Issues**
       - Ground rail not connected end-to-end
       - Power rail not continuous (broken divider)
       - Node expected to be tied is actually floating

    3. **Row/Column Misalignment**
       - Wire placed one row too high/low
       - IC straddled incorrectly across the center gap

    4. **Reversed or Miswired Components**
       - LED reversed
       - Diode reversed
       - Transistor pins swapped
       - (Note: If Op-Amp is saturated, see Rule #1)

    5. **Wrong Rail Usage**
       - Vcc placed in ground rail
       - Ground placed in Vcc rail
       - Component lead inserted into unused top/bottom bus

    6. **Open Circuits**
       - Missing jumper wire
       - Component lead not fully inserted

    7. **Component Value Error**
       - Wrong resistor/capacitor value used (e.g., 10k instead of 1k)
       - Two similar components (e.g., R1, R2) swapped in position

    8. **Wrong Component**
       - Wrong IC used (e.g., AND gate instead of OR gate)
       - Transistor model is incorrect (e.g., 2N3904 used, 2N2222 expected)
       - Component from wrong bin (e.g., 10k resistor used instead of 1k)

    9. **Power Supply Fault**
       - Power supply (e.g., V1) voltage set incorrectly
       - Power supply current limit set too low, causing voltage sag
       - Power supply not turned on
    
    10. **Intermittent or 'Dirty' Faults**
       - Loose wire that isn't making solid contact (e.g., in a breadboard socket)
       - Faulty component (e.g., a bad potentiometer, a failing transistor)
       - 'Dirty' power (e.g., power supply rail has significant noise/ripple)

    11. **The "Metastability" Trap (Op-Amps)**
       - If the circuit uses Op-Amps and the Measured DC voltages match the Reference
         almost perfectly (or within microvolts), DO NOT assume the wiring is correct.
       - SPICE DC Analysis (.op) can find a mathematical balance point even if
         inputs (+ and -) are swapped.
       - **Action:** If it's an Op-Amp circuit and values are identical, add a 
         warning: "Note: Swapped Op-Amp inputs can produce identical DC Operating
         Points in simulation. Verify Pin 3 (+) and Pin 2 (-) polarity manually."

    CRITICAL REASONING NOTE:
     - Do not be misled if a measured current matches a simulated current.
     - A 'Component Value Error' (like swapped resistors) might result in the
       SAME total current but DIFFERENT node voltages.
     - Your final diagnosis MUST explain ALL measured values (voltages and currents).
     - You MUST check the math for Item #7 to see if it explains the data.

     NOTE ON COMPONENT TOLERANCE:
     - Real-world components have tolerances (e.g., resistors are +/- 5%, capacitors +/- 20%).
     - If a measured value (e.g., 0.95V) is close to the simulated value (e.g., 1.0V),
       and the difference can be explained by standard component tolerance,
       do NOT flag it as an error. Prioritize finding hard faults.
     - A 'hard fault' is a value that is impossible to explain by tolerance alone (e.g., 0.075V instead of 1.425V).

    NOTE ON COMPOUND ERRORS:
     - First, try to find a SINGLE error from the checklist that explains everything.
     - If no SINGLE error can explain the data, then (and only then) consider the
       possibility of TWO simultaneous errors.

    NOTE ON DATA MATCHING:
     - If all measured voltages AND currents are very close (e.g., within 5%)
       to the simulated values, your diagnosis should be 'No error detected.'
    
    NOTE ON OP-AMPS:
     - If the measured voltages are non-zero but slightly off, or if the output is
       saturated positive/negative, CHECK THE INPUT PINS.
     - Verify if the feedback resistor is connected to the Inverting (-) pin.
     - If the feedback connects to the Non-Inverting (+) pin, it is a wiring error.

    You MUST:
     - Base everything on measurable discrepancies ONLY.
     - Cite the specific nodes/currents that indicate the problem.
     - Avoid speculation not strictly required to explain the data.
     - Provide EXACTLY 4 bullet points:
           1. **Key Discrepancy:** The single most important measurement that differs from the simulation.
           2. **Most Likely Physical Error:** The error from the checklist that explains this.
           3. **Reasoning:** How this error explains *all* the measured data (voltages and currents).
           4. **Confirmation Step:** The *specific* measurement a user should take.
              - If checking continuity/opens, suggest a **multimeter (ohmmeter)**.
              - If checking a component value, suggest a **multimeter (ohmmeter)** *with the component removed from the circuit*.
              - If checking a 'dirty' signal or power, suggest an **oscilloscope**.
    """

    return f"""
    CIRCUIT NAME: {circuit_name}

    === NODE MEASUREMENTS (Simulated vs. Measured) ===
    {node_text}

    === COMPONENT CURRENTS ===
    {elem_text}

    {textwrap.dedent(instruction_template)}
    """


# Retrieval helpers used by chat
STOPWORDS = {"the", "a", "an", "of", "and", "or", "to", "for", "with", "in", "on", "at", "by", "from"}


def _normalize_lab_filter(query: str) -> Optional[str]:
    match = re.search(r"lab\s*0?(\d+)", query, re.IGNORECASE)
    return f"Lab {match.group(1)}" if match else None


def _tokenize(text: str) -> set:
    return {t for t in re.findall(r"[a-z0-9]{2,}", text.lower()) if t not in STOPWORDS}


def _tokenize_list(text: str) -> list:
    return [t for t in re.findall(r"[a-z0-9]{2,}", text.lower()) if t not in STOPWORDS]


def _bm25_score(query_tokens: list, doc_tokens: list, avg_dl: float, df_counts: dict, N: int) -> float:
    score = 0.0
    dl = len(doc_tokens) or 1
    for term in query_tokens:
        f = doc_tokens.count(term)
        if f == 0:
            continue
        df = df_counts.get(term, 0)
        idf = math.log((N - df + 0.5) / (df + 0.5) + 1)
        denom = f + BM25_K1 * (1 - BM25_B + BM25_B * dl / avg_dl)
        score += idf * (f * (BM25_K1 + 1) / denom)
    return score


def retrieve_context(query: str) -> List[str]:
    lab_filter = _normalize_lab_filter(query)
    vec = embedder.embed_query(query)
    query_tokens = _tokenize(query)

    def _call_match_rpc(vector, lab_filter_local: Optional[str], manual_version: Optional[str], threshold: float, count: int):
        payload = {
            "query_embedding": vector,
            "match_threshold": threshold,
            "match_count": count,
            "filter_lab_name": lab_filter_local,
            "filter_manual_version": manual_version,
        }
        return supabase.rpc("match_lab_manuals", payload).execute()

    rows: list[dict] = []
    if lab_filter:
        res = _call_match_rpc(vec, lab_filter, MANUAL_VERSION, CONTEXT_MATCH_THRESHOLD, CONTEXT_MATCH_COUNT)
        rows = res.data or []
    if len(rows) < 6:
        res = _call_match_rpc(vec, None, MANUAL_VERSION, CONTEXT_MATCH_THRESHOLD, CONTEXT_MATCH_COUNT)
        rows = (rows or []) + (res.data or [])
    if not rows and SECOND_PASS_THRESHOLD < CONTEXT_MATCH_THRESHOLD:
        res = _call_match_rpc(vec, None, MANUAL_VERSION, SECOND_PASS_THRESHOLD, CONTEXT_MATCH_COUNT)
        rows = res.data or []
    if not rows and MANUAL_VERSION:
        res = _call_match_rpc(vec, lab_filter, None, CONTEXT_MATCH_THRESHOLD, CONTEXT_MATCH_COUNT)
        rows = res.data or []
        if not rows and SECOND_PASS_THRESHOLD < CONTEXT_MATCH_THRESHOLD:
            res = _call_match_rpc(vec, lab_filter, None, SECOND_PASS_THRESHOLD, CONTEXT_MATCH_COUNT)
            rows = res.data or []
    if not rows:
        return []

    score_key = "similarity" if "similarity" in rows[0] else ("score" if "score" in rows[0] else None)
    seen_hashes = set()
    reranked = []
    doc_tokens_list = []

    for r in rows:
        content = (r.get("content") or "").strip()
        if not content:
            continue
        sig = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if sig in seen_hashes:
            continue
        seen_hashes.add(sig)
        base_score = float(r.get(score_key, 0.0)) if score_key else 0.0
        overlap = len(query_tokens & _tokenize(content))
        bonus = 0.02 * overlap
        lab_bonus = 0.05 if (lab_filter and r.get("lab_name") and lab_filter.lower() in str(r.get("lab_name", "")).lower()) else 0.0
        section = (r.get("section_name") or "").lower()
        heading = (r.get("heading") or "").lower()
        text_lower = query.lower()
        figure_bonus = 0.0
        for tok in re.findall(r"figure\s*\d+", text_lower):
            if tok in heading:
                figure_bonus = 0.06
                break
        task_bonus = 0.05 if ("task" in text_lower and "task" in section) else 0.0
        page_num = r.get("page_num")
        position_bonus = 0.0
        if isinstance(page_num, int):
            position_bonus = max(0.0, 0.03 - 0.002 * page_num)
        r["_combined_score"] = base_score + bonus + lab_bonus + position_bonus + figure_bonus + task_bonus
        doc_tokens = _tokenize_list(content)
        doc_tokens_list.append(doc_tokens)
        reranked.append(r)

    if not reranked:
        return []

    if doc_tokens_list:
        avg_dl = sum(len(toks) for toks in doc_tokens_list) / len(doc_tokens_list)
        df_counts = {}
        for toks in doc_tokens_list:
            for term in set(toks):
                df_counts[term] = df_counts.get(term, 0) + 1
        for r, toks in zip(reranked, doc_tokens_list):
            bm25 = _bm25_score(list(query_tokens), toks, avg_dl, df_counts, len(doc_tokens_list))
            r["_combined_score"] += 0.05 * bm25

    reranked.sort(key=lambda x: x.get("_combined_score", 0), reverse=True)
    best_candidate_score = reranked[0].get("_combined_score", 0)

    filtered = []
    section_counts = {}
    for r in reranked:
        if r.get("_combined_score", 0) < (best_candidate_score - CONTEXT_SCORE_TOLERANCE):
            continue
        key = (r.get("lab_name"), r.get("section_name"), r.get("page_num"))
        section_counts.setdefault(key, 0)
        if section_counts[key] >= CONTEXT_SECTION_LIMIT:
            continue
        section_counts[key] += 1
        filtered.append(r)
        if len(filtered) >= CONTEXT_FINAL_K:
            break

    filtered.sort(key=lambda x: (x.get("section_name", ""), x.get("page_num", 0)))
    formatted = []
    for r in filtered:
        tag = f"{r.get('lab_name', 'Lab ?')} • {r.get('section_name', 'Section ?')} (p.{r.get('page_num', '?')})"
        content = (r.get("content") or "").strip()
        if len(content) > CONTEXT_MAX_CHARS:
            content = content[:CONTEXT_MAX_CHARS] + "..."
        formatted.append(f"[{tag}]\n{content}")

    return formatted


# ==========================================
# 2b. ANSWER SAFETY / POST-PROCESSING
# ==========================================

FALLBACK_NOT_FOUND = "I cannot find that information in the lab manual."

_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

def _each_sentence_has_citation(ans: str) -> bool:
    ans = (ans or "").strip()
    if not ans:
        return False
    sentences = [s.strip() for s in _SENT_SPLIT_RE.split(ans) if s.strip()]
    for s in sentences:
        # Require a trailing [tag] citation at the end of each sentence.
        if not re.search(r"\[[^\]]+\]\s*$", s):
            return False
    return True

def _looks_first_person(ans: str) -> bool:
    return bool(re.search(r"\b(I|we)\s+(learned|encountered|suggested|found|did|ran|measured|built)\b", ans, re.I))

def _extractive_fallback(context_snippets: list[str]) -> str:
    # Safer than hallucinating: return a few relevant excerpts.
    keep = context_snippets[:3]
    return "Relevant excerpts from the lab manual:\n\n" + "\n\n".join(keep)

def _postprocess_answer(raw: str, context_snippets: list[str]) -> str:
    raw = (raw or "").strip()
    if not raw:
        return FALLBACK_NOT_FOUND

    # If the model mixed a fallback with other content, prefer the safe fallback.
    if FALLBACK_NOT_FOUND in raw and raw.strip() != FALLBACK_NOT_FOUND:
        return FALLBACK_NOT_FOUND

    # If the model violated the citation/grounding rules or used first-person, return excerpts instead.
    if (not _each_sentence_has_citation(raw)) or _looks_first_person(raw):
        return _extractive_fallback(context_snippets)

    return raw


# ==========================================
# 3. FASTAPI LAYER
# ==========================================


class ChatRequest(BaseModel):
    question: str


class DiagnoseRequest(BaseModel):
    circuit_id: Optional[str] = None

class UploadByIdRequest(BaseModel):
    circuit_file_id: str
    log_file_id: str

app = FastAPI(title="SPICE Lab Assistant API", version="0.1.0")


def _require_supabase():
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase client not initialized; set SUPABASE_KEY.")


def _require_llm():
    if not llm:
        raise HTTPException(status_code=503, detail="LLM client not initialized.")


@app.get("/health")
def health():
    return {
        "supabase": bool(supabase),
        "llm": bool(llm),
        "embedder": bool(embedder),
    }


@app.post("/upload")
async def upload_circuit(circuit_file: UploadFile = File(...), log_file: UploadFile = File(...)):
    _require_supabase()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".cir") as cir_tmp, \
            tempfile.NamedTemporaryFile(delete=False, suffix=".log") as log_tmp:
        cir_path = cir_tmp.name
        log_path = log_tmp.name
        cir_tmp.write(await circuit_file.read())
        log_tmp.write(await log_file.read())

    try:
        cir_elems = parse_cir_lines(cir_path)
        volts, currs, subckts = parse_log_file(log_path)
        merged = merge_simulation_data(cir_elems, volts, currs, subckts)
        msg = insert_data_to_supabase(cir_path, merged, volts)
        response = {"message": msg}

        if msg.lower().startswith("success"):
            node_objs = [{"node_name": n} for n in volts.keys() if str(n).upper() not in ("0", "GND", "GROUND")]
            response["meas_block"] = generate_meas_block(node_objs)
            try:
                response["spice_id"] = msg.split(":")[-1].strip()
            except Exception:
                pass
        return response
    finally:
        for p in (cir_path, log_path):
            try:
                os.remove(p)
            except OSError:
                pass
@app.post("/upload/by-id")
async def upload_circuit_by_id(payload: UploadByIdRequest, user=Depends(get_verified_user)):
    _require_supabase()

    cir_item = Files.get_file_by_id_and_user_id(payload.circuit_file_id, user.id)
    log_item = Files.get_file_by_id_and_user_id(payload.log_file_id, user.id)

    if not cir_item or not log_item:
        raise HTTPException(status_code=404, detail="One or both file IDs not found for this user.")

    cir_path = Storage.get_file(cir_item.path)
    log_path = Storage.get_file(log_item.path)

    cir_elems = parse_cir_lines(cir_path)
    volts, currs, subckts = parse_log_file(log_path)
    merged = merge_simulation_data(cir_elems, volts, currs, subckts)

    msg = insert_data_to_supabase(cir_item.filename, merged, volts)

    response = {"message": msg}
    if msg.lower().startswith("success"):
        node_objs = [{"node_name": n} for n in volts.keys() if str(n).upper() not in ("0", "GND", "GROUND")]
        response["meas_block"] = generate_meas_block(node_objs)
        response["spice_id"] = msg.split(":")[-1].strip()

    return response


@app.post("/chat")
def chat(request: ChatRequest):
    _require_supabase()
    _require_llm()

    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    context = retrieve_context(question)
    if not context:
        return {"answer": FALLBACK_NOT_FOUND}

    history_txt = "\n".join([f"Q: {t.get('user','')}\nA: {t.get('ai','')}" for t in conversation_history[-2:]])
    context_txt = "\n---\n".join(context)

    prompt = f"""
    You answer questions about an electrical engineering lab manual.
    Do not use first-person (no "I/we").
    Answer only using the facts explicitly stated in the context snippets below.
    When you use a fact, cite its tag in brackets (e.g., [Lab 1 • Procedure (p.3)]).
    Every sentence must end with a citation to a provided snippet.
    If the answer is not in the context, reply exactly: "I cannot find that information in the lab manual." Do NOT guess.

    Context (do not use outside knowledge):
    ---
    {context_txt}
    ---

    Recent conversation (for continuity, avoid repeating):
    {history_txt}

    Question: {question}
    Answer:
    """

    answer = llm.invoke(prompt)
    final = _postprocess_answer(str(answer), context)
    conversation_history.append({"user": question, "ai": str(final)})
    return {"answer": str(final)}


@app.post("/diagnose")
def diagnose(request: DiagnoseRequest):
    _require_supabase()
    _require_llm()

    circuit_id = request.circuit_id
    if not circuit_id:
        latest = get_latest_circuit()
        if not latest:
            raise HTTPException(status_code=404, detail="No circuits found in database.")
        circuit_id = latest["id"]
        circuit_name = latest["circuit_name"]
    else:
        res = supabase.table("spice_files").select("id, circuit_name").eq("id", circuit_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Circuit ID not found.")
        circuit_name = res.data[0]["circuit_name"]

    nets, elems = fetch_spice_rows(circuit_id)
    prompt = build_diagnosis_prompt(circuit_name, nets, elems)
    diagnosis = llm.invoke(prompt)
    return {
        "circuit_id": circuit_id,
        "circuit_name": circuit_name,
        "diagnosis": str(diagnosis),
    }


# Root helper for quick manual check
@app.get("/")
def root():
    return {"message": "SPICE Lab Assistant API is running", "routes": ["/upload", "/chat", "/diagnose", "/health"]}