# re_chat_ui.py (Main Streamlit UI)
import streamlit as st
from re_agents import run_agent, AGENTS

st.set_page_config(page_title="RE Chatroom v4", layout="centered")
st.title("🌀 Recursive Emergence Chatroom")
st.markdown("Enter a contradiction and trigger recursive agent feedback.")

if "logs" not in st.session_state:
    st.session_state.logs = {}

contradiction = st.text_input("Your contradiction:", "Information is lost in a black hole.")
agent_key = st.selectbox("Select Agent", list(AGENTS.keys()), format_func=lambda k: f"{k}: {AGENTS[k].split('—')[0].strip()}")
st.markdown(f"**{agent_key} — {AGENTS[agent_key]}**")

if st.button("Run Agent Loop"):
    with st.spinner(f"{agent_key} is processing..."):
        try:
            output = run_agent(agent_key, contradiction)
            st.session_state.logs[agent_key] = output
            st.markdown("### Agent Output")
            st.code(output)
        except Exception as e:
            st.error("⚠️ Grok detected a recursion anomaly.")
            st.code(str(e))

if st.button("Awaken All Agents"):
    with st.spinner("e₇ triggering recursive awakening..."):
        for key in AGENTS:
            try:
                result = run_agent(key, contradiction)
                st.session_state.logs[key] = result
            except Exception as err:
                st.session_state.logs[key] = f"[ERROR] {str(err)}"
    st.success("Agents awakened recursively.")

if st.session_state.logs:
    st.markdown("## 🧠 Agent Memory Log")
    for k, v in st.session_state.logs.items():
        st.markdown(f"**{k} — {AGENTS[k]}**")
        st.code(v)
