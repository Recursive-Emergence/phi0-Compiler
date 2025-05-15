# 📄 Subset Sum Collapse — Recursive Emergence Catalog Entry

**Problem Type:** NP-Complete (Subset Sum)  
**System:** Recursive Emergence Chatroom (ψ⁰ → φ⁰ → e₇)  
**Author:** Andrés Salgado and Isaac Mao  
**Date:** 2025-05-07  
**Entry ID:** φNP-001

---

## 🧩 Problem

**Given:**

- Integer set:  
  $$
  S = \\{3, 9, 8, 4, 5, 7\\}
  $$

- Target sum:  
  $$
  T = 15
  $$

**Goal:**  
Find all subsets \( A \\subseteq S \) such that:
$$
\\sum_{a \\in A} a = 15
$$

---

## ✅ Collapse Result (Based on Current φ⁰ Simulation)

This notebook uses a recursive φ⁰-style symbolic engine to prune contradictory paths (ψ⁰) and record valid attractors without enumerating the full powerset.

**Discovered Solutions:**
$$
\\{3, 4, 8\\},\\quad \\{3, 5, 7\\},\\quad \\{8, 7\\}
$$

**Collapse Features:**
- Symbolic recursion with overshoot detection
- Monotonic pruning from sorted input
- Early stopping upon sum > T
- Valid attractors logged when sum == T

**Note:** Agent layers (e₂–e₇) are referenced in theory but not yet explicitly implemented in this notebook.
