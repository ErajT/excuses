import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain import LLMChain
from dotenv import load_dotenv
import os

# ==============================
# Setup
# ==============================
# os.environ["OPENAI_API_KEY"] = "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"

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Initialize LLM (OpenRouter)
llm = ChatOpenAI(
     openai_api_key=api_key,
    openai_api_base="https://openrouter.ai/api/v1",
    model="openai/gpt-oss-20b:free",
    temperature=0.7,  # bit higher for funnier roasts
)

# Prompt Template for Excuse Detector + Roast
prompt = ChatPromptTemplate.from_template("""
You are an AI agent that detects excuses in text messages.

For the given input, do the following:
1. Detect if it contains an excuse (Yes/No).
2. If Yes, classify it as:
   - Believable
   - Nonsense
   - Suspicious
3. Provide a short explanation for your reasoning.
4. Roast the excuse with humor, sarcasm, or playful "brainrot" style banter.
   - Example roasts:
     - "Bro even ChatGPT can come up with better excuses 💀"
     - "Wi-Fi died? More like your motivation died."
     - "This excuse is weaker than my willpower on leg day."
     - "Dog ate your homework? Congrats, you just unlocked the 1999 excuse DLC."

Text: "{text}"
""")

# Build LangChain pipeline
excuse_chain = LLMChain(
    llm=llm,
    prompt=prompt,
    output_parser=StrOutputParser()
)

# ==============================
# Streamlit UI
# ==============================
st.set_page_config(page_title="AI Excuse Detector 🤖📝", page_icon="📝", layout="centered")

st.title("🤖 AI Excuse Detector & Roaster")
st.write("Paste your excuse below and let the AI **analyze + roast** it.")

# User input
user_excuse = st.text_area("Enter your excuse:", placeholder="Sorry I was late, my Wi-Fi died...")

if st.button("Analyze My Excuse 🚀"):
    if user_excuse.strip() == "":
        st.warning("Please enter some text first.")
    else:
        with st.spinner("Analyzing your excuse..."):
            result = excuse_chain.run({"text": user_excuse})

        # Split response into parts (optional formatting)
        st.subheader("🔍 Analysis & Roast")
        st.write(result)

# Fun examples
st.sidebar.title("Try Examples")
examples = [
    "Sorry I missed class, my Wi-Fi died.",
    "The deadline was missed because a seagull stole my laptop.",
    "My dog ate my homework.",
    "Sorry I didn’t reply, I was busy manifesting my future.",
    "Meeting moved to 3pm."
]

for ex in examples:
    if st.sidebar.button(ex):
        user_excuse = ex
        with st.spinner("Analyzing your excuse..."):
            result = excuse_chain.run({"text": ex})
        st.subheader("🔍 Analysis & Roast")
        st.write(result)
