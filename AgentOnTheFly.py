import json
import os
import atexit
from typing import Optional
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import ToolSet, CodeInterpreterTool, BingGroundingTool, MessageTextContent, FileSearchTool, FilePurpose

from azure.identity import DefaultAzureCredential
import streamlit.components.v1 as components
import streamlit as st
from PIL import Image
from pprint import pformat

import time
# Author: Ron Dagdag
# Date: 03/02/2025
# Version: 1.0

# Add state persistence functions
def save_session_state():
    try:
        state_to_save = {
            "rag_agent_id": st.session_state.get("rag_agent_id"),
            "vector_store_id": st.session_state.get("vector_store_id"),
            "last_file": st.session_state.get("last_file", "")
        }
        with open(".session_state.json", "w") as f:
            json.dump(state_to_save, f)
        print("Session state saved successfully")
    except Exception as e:
        print(f"Error saving session state: {e}")

def load_session_state():
    try:
        if os.path.exists(".session_state.json"):
            with open(".session_state.json", "r") as f:
                saved_state = json.load(f)
                return saved_state
        return None
    except Exception as e:
        print(f"Error loading session state: {e}")
        return None


# Set page config
st.set_page_config(
    page_title = "Agent Service Demo",
    page_icon = ":ninja:",
    layout = "wide"
)

# Check if environment variables are set
env_vars = ["project_connstring", "gpt_model"]
for var_name in env_vars:
    if var_name not in st.session_state:
        st.session_state[var_name] = os.getenv(("AZURE_FOUNDRY_" + var_name).upper())

missing_vars = [var for var in env_vars if not st.session_state.get(var)]
if missing_vars:
    missing_vars_str = ", ".join([("AZURE_FOUNDRY_" + var).upper() for var in missing_vars])
    st.error(f"Environment variable(s) {missing_vars_str} are not set. Please set them to make this UI Demo Kit fully operational.")
    # st.stop()

# Initialise key UI Demo Kit variables
project_connstring = st.session_state.get("project_connstring")
gpt_model = st.session_state.get("gpt_model")

# Initialize session state and clean up old resources
if "initialized" not in st.session_state:
    # Load previous session state
    saved_state = load_session_state()
    
    if saved_state:
        try:
            # Initialize AI Project client
            project_client = AIProjectClient.from_connection_string(
                credential=DefaultAzureCredential(),
                conn_str=project_connstring
            )
            
            # Clean up resources from previous session
            if saved_state.get("rag_agent_id"):
                try:
                    project_client.agents.delete_agent(saved_state["rag_agent_id"])
                    print(f"Cleaned up previous RAG agent: {saved_state['rag_agent_id']}")
                except Exception as e:
                    print(f"Error cleaning up previous RAG agent: {e}")
                    
            if saved_state.get("vector_store_id"):
                try:
                    project_client.agents.delete_vector_store(saved_state["vector_store_id"])
                    print(f"Cleaned up previous vector store: {saved_state['vector_store_id']}")
                except Exception as e:
                    print(f"Error cleaning up previous vector store: {e}")
                    
            # Clean up state file
            if os.path.exists(".session_state.json"):
                os.remove(".session_state.json")
        except Exception as e:
            print(f"Error during startup cleanup: {e}")
    
    st.session_state["initialized"] = True

# Streamlit state to store session state variables
if "interpreter_image" not in st.session_state:
    st.session_state["interpreter_image"] = ""
if "interpreter_code" not in st.session_state:
    st.session_state["interpreter_code"] = ""
if "progress" not in st.session_state:
    st.session_state["progress"] = 0
if "status_message" not in st.session_state:
    st.session_state["status_message"] = ""
if "rag_agent_id" not in st.session_state:
    st.session_state["rag_agent_id"] = None
if "vector_store_id" not in st.session_state:
    st.session_state["vector_store_id"] = None
if "project_client" not in st.session_state:
    st.session_state["project_client"] = None

# Set sidebar navigation
st.sidebar.title("Instructions:")
st.sidebar.markdown(
    """
    This Streamlit app for running Agent on the fly. 

    For source code, setup instructions and more details, visit the [GitHub repo](https://github.com/rondagdag/azure-ai-agents-web-client).
    """
)
menu = st.sidebar.radio("Choose a capability:", ("Code Interpreter", "RAG", "RAG + Code Interpreter"))

# Helper Function for Code Interpreter capability
def update_progress(progress_bar, progress, message):
    st.session_state.progress = progress
    st.session_state.status_message = message
    progress_bar.progress(progress, text=message)

def code_interpreter(prompt, conn_str=project_connstring, model=gpt_model):
    st.session_state["interpreter_image"] = ""
    st.session_state["interpreter_code"] = ""
    st.session_state.progress = 0
    st.session_state.status_message = ""

    try:
        progress_bar = st.progress(0)
        update_progress(progress_bar, 10, "Initializing...")

        # Initiate AI Project client
        project_client = AIProjectClient.from_connection_string(
            credential = DefaultAzureCredential(),
            conn_str = conn_str
        )
        update_progress(progress_bar, 20, "Connected to AI Project service")

        # Add Code Interpreter to the Agent's ToolSet
        toolset = ToolSet()
        code_interpreter_tool = CodeInterpreterTool()
        toolset.add(code_interpreter_tool)
        update_progress(progress_bar, 30, "Added Code Interpreter tool")

        # Initiate Agent Service
        agent = project_client.agents.create_agent(
            model = model,
            name = "code-interpreter-agent",
            instructions = "You are a helpful data analyst. You can use Python to perform required calculations.",
            toolset = toolset
        )
        print(f"Created agent, agent ID: {agent.id}")
        update_progress(progress_bar, 40, "Created AI agent")

        # Create a thread
        thread = project_client.agents.create_thread()
        print(f"Created thread, thread ID: {thread.id}")
        update_progress(progress_bar, 50, "Created conversation thread")

        # Create a message
        message = project_client.agents.create_message(
            thread_id = thread.id,
            role = "user",
            content = prompt
        )
        print(f"Created message, message ID: {message.id}")
        update_progress(progress_bar, 60, "Sent message to agent")

        # Run the agent
        run = project_client.agents.create_and_process_run(
            thread_id = thread.id,
            assistant_id = agent.id
        )
        update_progress(progress_bar, 70, "Processing your request...")

        # Check the run status
        if run.status == "failed":
            project_client.agents.delete_agent(agent.id)
            print(f"Deleted agent, agent ID: {agent.id}")
            progress_bar.empty()
            return f"Run failed: {run.last_error}"

        time.sleep(10)  # Increase delay if needed
        update_progress(progress_bar, 80, "Getting response from agent...")

        # Get the last message from the agent
        messages = project_client.agents.list_messages(thread_id=thread.id)
        sorted_messages = sorted(messages.data, key=lambda x: x.created_at)
        last_msg = sorted_messages[-1]
        
        # Handle message content
        file_name = "interpreter_image_file.png"
        result = ""
        if last_msg and last_msg.content:
            for content_item in last_msg.content:
                content_type = getattr(content_item, 'type', None)
                if content_type == 'text':
                    result += content_item.text.value + "\n"
                elif content_type == 'image_file':
                    result += "[Image generated by the agent]\n"
                    # Save the image file
                    project_client.agents.save_file(
                        file_id=content_item.image_file.file_id,
                        file_name=file_name
                    )
                    print(f"Downloaded image, file name: {file_name}")
                    st.session_state['interpreter_image'] = file_name
            result = result.strip()
        else:
            result = "No response from agent."
            
        update_progress(progress_bar, 90, "Processing response...")

        # Retrieve the Python code snippet
        run_details = project_client.agents.list_run_steps(
            thread_id = thread.id,
            run_id = run.id
        )
        for steps in run_details.data:
            if getattr(steps.step_details, 'type', None) == "tool_calls":
                for calls in steps.step_details.tool_calls:
                    input_value = getattr(calls.code_interpreter, 'input', None)
                    if input_value:
                        print("Extracted Python code snippet")
                        st.session_state['interpreter_code'] = input_value

        # Delete the agent once done
        project_client.agents.delete_agent(agent.id)
        print(f"Deleted agent, agent ID: {agent.id}")
        update_progress(progress_bar, 100, "Complete!")
        time.sleep(1)
        progress_bar.empty()

        return result

    except Exception as e:
        progress_bar.empty()
        st.error(f"An error occurred: {e}")
        return f"An error occurred: {e}"

# Helper Function for RAG capability
def rag_search(file_obj, prompt, conn_str=project_connstring, model=gpt_model):
    st.session_state["interpreter_image"] = ""  # Reset image state
    st.session_state.progress = 0
    st.session_state.status_message = ""
    
    try:
        progress_bar = st.progress(0)
        update_progress(progress_bar, 10, "Initializing...")

        # Initialize AI Project client if not already initialized
        if not st.session_state["project_client"]:
            st.session_state["project_client"] = AIProjectClient.from_connection_string(
                credential=DefaultAzureCredential(),
                conn_str=conn_str
            )
        project_client = st.session_state["project_client"]
        update_progress(progress_bar, 20, "Connected to AI Project service")

        # Create agent if not exists
        if not st.session_state["rag_agent_id"]:
            # Save uploaded file temporarily
            temp_file_path = f"temp_{file_obj.name}"
            with open(temp_file_path, "wb") as f:
                f.write(file_obj.getvalue())
            update_progress(progress_bar, 30, "Saved uploaded file")

            # Upload the file
            file = project_client.agents.upload_file_and_poll(
                file_path=temp_file_path,
                purpose=FilePurpose.AGENTS
            )
            print(f"Uploaded file, file ID: {file.id}")
            update_progress(progress_bar, 40, "Uploaded file to AI service")

            # Create vector store if not exists or if new file is uploaded
            if not st.session_state["vector_store_id"]:
                vector_store = project_client.agents.create_vector_store_and_poll(
                    file_ids=[file.id],
                    name=f"vectorstore_{file_obj.name}"
                )
                st.session_state["vector_store_id"] = vector_store.id
                print(f"Created vector store, vector store ID: {vector_store.id}")
            update_progress(progress_bar, 50, "Created vector store for document search")

            # Create file search tool
            file_search_tool = FileSearchTool(vector_store_ids=[st.session_state["vector_store_id"]])
            update_progress(progress_bar, 60, "Initialized document search tool")


            agent = project_client.agents.create_agent(
                model=model,
                name="rag-agent",
                instructions="You are a helpful agent which provides answer ONLY from the search.",
                tools=file_search_tool.definitions,
                tool_resources=file_search_tool.resources,
            )
            st.session_state["rag_agent_id"] = agent.id
            print(f"Created agent, agent ID: {agent.id}")
        update_progress(progress_bar, 70, "Created AI agent")

        # Create thread and message
        thread = project_client.agents.create_thread()
        message = project_client.agents.create_message(
            thread_id = thread.id,
            role = "user",
            content = prompt
        )
        print(f"Created message, message ID: {message.id}")
        update_progress(progress_bar, 80, "Sent question to agent")

        # Run the agent
        run = project_client.agents.create_and_process_run(
            thread_id=thread.id,
            assistant_id=st.session_state["rag_agent_id"]
        )
        update_progress(progress_bar, 85, "Processing your question...")

        # Check the run status
        if run.status == "failed":
            progress_bar.empty()
            return f"Run failed: {run.last_error}"

        #time.sleep(30)  # Increase delay if needed
        update_progress(progress_bar, 90, "Getting response from agent...")

        # Get the last message from the agent
        messages = project_client.agents.list_messages(thread_id=thread.id)
        sorted_messages = sorted(messages.data, key=lambda x: x.created_at)
        print(f"Messages: {pformat(sorted_messages)}")
        last_msg = sorted_messages[-1]
        result = last_msg.content[0].text.value if last_msg else "No response from agent."
        update_progress(progress_bar, 95, "Processing response...")

        save_session_state()
        # Cleanup temporary file
        if 'temp_file_path' in locals():
            os.remove(temp_file_path)
        
        update_progress(progress_bar, 100, "Complete!")
        time.sleep(1)
        progress_bar.empty()

        return result

    except Exception as e:
        if 'temp_file_path' in locals():
            os.remove(temp_file_path)
        progress_bar.empty()
        st.error(f"An error occurred: {e}")
        return f"An error occurred: {e}"

# Helper Function for Combined RAG and Code Interpreter capability
def rag_with_code_interpreter(file_obj, prompt, conn_str=project_connstring, model=gpt_model):
    st.session_state["interpreter_image"] = ""
    st.session_state["interpreter_code"] = ""
    st.session_state.progress = 0
    st.session_state.status_message = ""
    
    try:
        progress_bar = st.progress(0)
        update_progress(progress_bar, 10, "Initializing...")

        # Initialize AI Project client
        project_client = AIProjectClient.from_connection_string(
            credential=DefaultAzureCredential(),
            conn_str=conn_str
        )
        update_progress(progress_bar, 20, "Connected to AI Project service")

        # Save and upload file
        temp_file_path = f"temp_{file_obj.name}"
        with open(temp_file_path, "wb") as f:
            f.write(file_obj.getvalue())
        update_progress(progress_bar, 30, "Saved uploaded file")

        # Upload the file
        file = project_client.agents.upload_file_and_poll(
            file_path=temp_file_path,
            purpose=FilePurpose.AGENTS
        )
        print(f"Uploaded file, file ID: {file.id}")
        update_progress(progress_bar, 40, "Uploaded file to AI service")

        # Create vector store
        vector_store = project_client.agents.create_vector_store_and_poll(
            file_ids=[file.id],
            name=f"vectorstore_{file_obj.name}"
        )
        print(f"Created vector store, vector store ID: {vector_store.id}")
        update_progress(progress_bar, 50, "Created vector store for document search")

        # Setup tools
        toolset = ToolSet()
        code_interpreter_tool = CodeInterpreterTool()
        toolset.add(code_interpreter_tool)
        print("Added Code Interpreter tool")
        
        file_search_tool = FileSearchTool(vector_store_ids=[vector_store.id])
        toolset.add(file_search_tool)
        print("Added File Search tool")

        update_progress(progress_bar, 60, "Added Code Interpreter and File Search tools")

        # Create agent with both capabilities
        agent = project_client.agents.create_agent(
            model=model,
            name="rag-code-interpreter-agent",
            instructions="You are a helpful agent that can analyze documents and generate Python code based on the document content. Use the file search to extract relevant information and then generate appropriate Python code for analysis when needed.",
            toolset = toolset
        )

        print(f"Created agent, agent ID: {agent.id}")
        update_progress(progress_bar, 70, "Created AI agent")

        # Create thread and message
        thread = project_client.agents.create_thread()
        message = project_client.agents.create_message(
            thread_id=thread.id,
            role="user",
            content=prompt
        )
        print(f"Created message, message ID: {message.id}")
        update_progress(progress_bar, 80, "Sent request to agent")

        # Run the agent
        run = project_client.agents.create_and_process_run(
            thread_id=thread.id,
            assistant_id=agent.id
        )
        update_progress(progress_bar, 85, "Processing your request...")

        if run.status == "failed":
            project_client.agents.delete_agent(agent.id)
            project_client.agents.delete_vector_store(vector_store.id)
            os.remove(temp_file_path)
            progress_bar.empty()
            return f"Run failed: {run.last_error}"

        update_progress(progress_bar, 90, "Getting response from agent...")

        # Get the last message from the agent
        messages = project_client.agents.list_messages(thread_id=thread.id)
        print(f"Messages: {pformat(messages)}")
        # Sort messages by creation time (ascending)
        sorted_messages = sorted(messages.data, key=lambda x: x.created_at)
        print(f"Messages: {pformat(sorted_messages)}")
        last_msg = sorted_messages[-1]
        content = last_msg.content

        
        # Handle multiple content types
        result = ""
        if last_msg and last_msg.content:
            for content in last_msg.content:
                content_type = getattr(content, 'type', None)
                if content_type == 'text':
                    result += content.text.value + "\n"
                elif content_type == 'image_file':
                    result += "[Image generated by the agent]\n"
                    # Save the image file
                    file_name = "interpreter_image_file.png"
                    project_client.agents.save_file(
                        file_id=content.image_file.file_id,
                        file_name=file_name
                    )
                    print(f"Downloaded image, file name: {file_name}")
                    st.session_state['interpreter_image'] = file_name
            result = result.strip()
        else:
            result = "No response from agent."

        # Get any generated code
        run_details = project_client.agents.list_run_steps(
            thread_id=thread.id,
            run_id=run.id
        )
        for steps in run_details.data:
            if getattr(steps.step_details, 'type', None) == "tool_calls":
                for tool_call in steps.step_details.tool_calls:
                    tool_type = getattr(tool_call, 'type', None)
                    if tool_type == 'code_interpreter':
                        input_value = tool_call.code_interpreter.input
                        if input_value:
                            print("Extracted Python code snippet")
                            st.session_state['interpreter_code'] = input_value

        # Cleanup
        project_client.agents.delete_agent(agent.id)
        project_client.agents.delete_vector_store(vector_store.id)
        os.remove(temp_file_path)
        
        update_progress(progress_bar, 100, "Complete!")
        time.sleep(1)
        progress_bar.empty()

        return result

    except Exception as e:
        if 'temp_file_path' in locals():
            os.remove(temp_file_path)
        if 'agent' in locals():
            project_client.agents.delete_agent(agent.id)
        if 'vector_store' in locals():
            project_client.agents.delete_vector_store(vector_store.id)
        progress_bar.empty()
        st.error(f"An error occurred: {e}")
        return f"An error occurred: {e}"

# Main screen
st.title("AI Agent on the Fly - Azure AI Foundry Agent Service")

if menu == "Code Interpreter":
    st.header("Agent to write code and execute in sandboxed environment")
    default_prompt = """Could you please analyse the movies and box office gross using the following data and producing a bar chart image.

Movie Title	Release Year	IMDb Rating	Rotten Tomatoes	Box Office Gross (USD)
Citizen Kane	1941	8.3	99%	$1.6 million
The Hoodlum Saint	1946	6.2	N/A	N/A
Cinderella	1950	7.3	98%	N/A
My Fair Lady	1964	7.8	95%	$72 million
Oliver!	1968	7.4	85%	$77.4 million
Rocky	1976	8.1	92%	$225 million
The Jerk	1979	7.1	83%	$73.7 million
Scarface	1983	8.3	81%	$66 million
Trading Places	1983	7.5	88%	$90.4 million
Goodfellas	1990	8.7	96%	$47.1 million
Pretty Woman	1990	7.1	64%	$463.4 million
The Pursuit of Happyness	2006	8.0	67%	$307.1 million
Slumdog Millionaire	2008	8.0	91%	$378.1 million
The Social Network	2010	7.7	96%	$224.9 million
Limitless	2011	7.4	70%	$161.8 million
The Wolf of Wall Street	2013	8.2	79%	$392 million
Joy	2015	6.6	60%	$101.1 million
Straight Outta Compton	2015	7.8	89%	$201.6 million
The White Tiger	2021	7.1	91%	N/A
Dumb Money	2023	7.2	84%	$45.1 million
"""
    prompt = st.text_area("Enter your prompt:", value=default_prompt, height=300)
    if st.button("Run"):
        st.session_state.progress = 0
        result = code_interpreter(prompt)
        st.text_area("Output:", value=str(result), height=200)
        if st.session_state.get('interpreter_image'):
            img = Image.open(st.session_state['interpreter_image'])
            st.image(img, caption="Image generated by Code Interpreter")
        if st.session_state.get('interpreter_code'):
            st.text_area("Python Code Snippet:", value=st.session_state['interpreter_code'], height=300)
    if st.button("Clear"):
        st.text_area("Output:", value="", height=200)
        st.session_state['interpreter_image'] = ''
        st.session_state['interpreter_code'] = ''

elif menu == "RAG":
    st.header("Retrieval Augmented Generation with Document Search")
    uploaded_file = st.file_uploader("Choose a document file", type=["doc", "docx", "go", "html", "java", "js", "json", "md", "pdf", "php", "pptx", "py", "rb", "sh", "tex", "ts", "txt"])
    
    # Clear exigent andre ifnew fileloaded
    if uploaded_file is not None and uploaded_file.name not in st.session_state.get("last_file", ""):
        if st.session_state["rag_agent_id"] and st.session_state["project_client"]:
            st.session_state["project_client"].agents.delete_agent(st.session_state["rag_agent_id"])
        if st.session_state["vector_store_id"] and st.session_state["project_client"]:
            st.session_state["project_client"].agents.delete_vector_store(st.session_state["vector_store_id"])
        st.session_state["rag_agent_id"] = None
        st.session_state["vector_store_id"] = None
        st.session_state["last_file"] = uploaded_file.name
    
    default_prompt = "What are the key points from this document?"
    prompt = st.text_area("Enter your question about the document:", value=default_prompt, height=150)
    
    if uploaded_file is not None and st.button("Run"):
        st.session_state.progress = 0
        result = rag_search(uploaded_file, prompt)
        print(result)
        st.text_area("Response:", value=str(result), height=300)
        if st.session_state.get('interpreter_image'):
            img = Image.open(st.session_state['interpreter_image'])
            st.image(img, caption="Image generated by RAG")
    
    if st.button("Clear"):
        if st.session_state["rag_agent_id"] and st.session_state["project_client"]:
            st.session_state["project_client"].agents.delete_agent(st.session_state["rag_agent_id"])
        if st.session_state["vector_store_id"] and st.session_state["project_client"]:
            st.session_state["project_client"].agents.delete_vector_store(st.session_state["vector_store_id"])
        st.session_state["rag_agent_id"] = None
        st.session_state["vector_store_id"] = None
        st.session_state["last_file"] = ""
        st.session_state['interpreter_image'] = ''
        st.text_area("Response:", value="", height=300)

elif menu == "RAG + Code Interpreter":
    st.header("Combined Document Analysis and Code Generation")
    uploaded_file = st.file_uploader("Choose a document file", type=["doc", "docx", "go", "html", "java", "js", "json", "md", "pdf", "php", "pptx", "py", "rb", "sh", "tex", "ts", "txt"])
    
    default_prompt = "Could you please analyse the movies and box office gross using the following data and producing a bar chart image."
    prompt = st.text_area("Enter your request:", value=default_prompt, height=150)
    
    if uploaded_file is not None and st.button("Run"):
        st.session_state.progress = 0
        result = rag_with_code_interpreter(uploaded_file, prompt)
        st.text_area("Response:", value=str(result), height=300)
        if st.session_state.get('interpreter_code'):
            st.text_area("Generated Python Code:", value=st.session_state['interpreter_code'], height=200)
        if st.session_state.get('interpreter_image'):
            img = Image.open(st.session_state['interpreter_image'])
            st.image(img, caption="Generated Visualization")
    
    if st.button("Clear"):
        st.session_state['interpreter_image'] = ''
        st.session_state['interpreter_code'] = ''
        st.text_area("Response:", value="", height=300)

else:
    st.header("Please, choose a capability from the sidebar.")