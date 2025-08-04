import time
import threading
import sys
import traceback
import inspect
import os
import json
from typing import Optional, Callable

# Make mlx_lm imports conditional for CI compatibility
try:
    from mlx_lm import load, stream_generate
    from mlx_lm.sample_utils import make_sampler
    MLX_LM_AVAILABLE = True
except ImportError:
    MLX_LM_AVAILABLE = False
    print("[WARN] mlx_lm not available in llm_handler.py - using mock")
    # Create mock mlx_lm functions
    def load(model_path):
        return (MockModel(model_path), MockTokenizer())
    
    def stream_generate(model, tokenizer, prompt, **kwargs):
        yield f"[MOCK LLM RESPONSE] Processed prompt: {prompt[:50]}..."
    
    def make_sampler(**kwargs):
        return lambda x: x  # Mock sampler
    
    class MockModel:
        def __init__(self, path):
            self.path = path
    
    class MockTokenizer:
        def __init__(self):
            pass

# Detect CI environment for tqdm protection
IS_CI_ENVIRONMENT = (
    os.getenv('GITHUB_ACTIONS') == 'true' or 
    os.getenv('CI') == 'true' or
    os.getenv('RUNNER_OS') is not None
)

# Configure environment to disable tqdm progress bars in CI
if IS_CI_ENVIRONMENT:
    os.environ['TQDM_DISABLE'] = '1'

from src.config import config
from src.utils.utils import log_text
from src.memory_monitor import memory_monitor
from src.config.settings_manager import SettingsManager
from src.professional_text_formatter import ProfessionalTextFormatter


class LLMHandler:
    """Handles loading and interacting with MLX Language Models for text processing."""

    def __init__(
        self,
        on_processing_complete_callback=None,
        on_status_update_callback=None,
        on_proofing_activity_callback=None,
    ):
        self.on_processing_complete = on_processing_complete_callback
        self.on_status_update_callback = on_status_update_callback
        self.on_proofing_activity_callback = on_proofing_activity_callback
        self._current_model_name = None
        self._model = None
        self._tokenizer = None
        self._load_lock = threading.Lock()
        self._proofing_prompt = config.DEFAULT_PROOFREAD_PROMPT
        self._letter_prompt = config.DEFAULT_LETTER_PROMPT
        self._selected_proofing_model_id = None
        self._selected_letter_model_id = None
        self._pending_request = None
        self.generation_params = {"max_tokens": config.LLM_MAX_TOKENS_TO_GENERATE}
        
        # Initialize professional text formatter
        self._professional_formatter = ProfessionalTextFormatter()
        
        # Log initialization and check for dependencies
        if not MLX_LM_AVAILABLE:
            log_text("LLM_HANDLER_INIT", "LLM handler initialized in CI mode - mlx_lm not available")
        else:
            log_text(
                "LLM_HANDLER_INIT",
                f"Initialized. Proofing prompt: '{self._proofing_prompt[:50]}...', Letter prompt: '{self._letter_prompt[:50]}...'",
            )

    def _log_status(self, message, color="black"):
        if self.on_status_update_callback:
            try:
                self.on_status_update_callback(message, color)
            except Exception as e_status_cb:
                log_text(
                    "LLM_STATUS_CB_ERROR",
                    f"Error in on_status_update_callback: {e_status_cb}",
                )

    def _load_model_worker(
        self, model_key: str, model_path: str, on_load_complete: callable
    ):
        log_text("LOAD_MODEL_WORKER", f"Worker started for model: {model_key}")
        load_start_time = time.time()
        success = False
        try:
            with self._load_lock:
                if self._current_model_name == model_key and self._model is not None:
                    log_text(
                        "LOAD_MODEL_WORKER",
                        f"Model '{model_key}' was already loaded. Skipping.",
                    )
                    success = True
                    if on_load_complete:
                        on_load_complete(True)
                    return

                if self._model is not None and self._current_model_name != model_key:
                    self._log_status(
                        f"Unloading previous model: {self._current_model_name}",
                        "orange",
                    )
                    del self._model, self._tokenizer
                    self._model, self._tokenizer, self._current_model_name = (
                        None,
                        None,
                        None,
                    )
                    log_text("LOAD_MODEL_WORKER", "Previous model unloaded.")

                self._log_status(
                    f"Loading LLM: {model_key} ({model_path})...", "orange"
                )
                
                try:
                    # Attempt to load model with tqdm protection
                    self._model, self._tokenizer = load(model_path)
                except AttributeError as e:
                    if "tqdm" in str(e) and "_lock" in str(e):
                        # Known tqdm threading issue in CI - retry with different approach
                        log_text("LOAD_MODEL_WARNING", f"tqdm threading issue detected, retrying: {e}")
                        time.sleep(0.5)  # Brief pause to let threads settle
                        
                        # Retry once more
                        try:
                            self._model, self._tokenizer = load(model_path)
                        except Exception as retry_error:
                            # If retry fails, re-raise original error
                            log_text("LOAD_MODEL_ERROR", f"Model load retry failed: {retry_error}")
                            raise e
                    else:
                        # Re-raise non-tqdm AttributeErrors
                        raise e
                
                self._current_model_name = model_key
                success = True
                load_duration = time.time() - load_start_time
                self._log_status(
                    f"LLM '{model_key}' loaded successfully ({load_duration:.2f}s).",
                    "green",
                )
                log_text(
                    "LOAD_MODEL_WORKER",
                    f"Model '{model_key}' loaded successfully in {load_duration:.2f}s.",
                )
        except Exception as e:
            load_duration = time.time() - load_start_time
            error_details = traceback.format_exc()
            self._log_status(
                f"Error loading LLM '{model_key}' after {load_duration:.2f}s: {e}",
                "red",
            )
            log_text(
                "LOAD_MODEL_ERROR",
                f"Error loading LLM '{model_key}' after {load_duration:.2f}s: {e}\n{error_details}",
            )
            with self._load_lock:
                self._model, self._tokenizer, self._current_model_name = (
                    None,
                    None,
                    None,
                )
            success = False
        finally:
            if on_load_complete:
                try:
                    on_load_complete(success)
                except Exception as cb_error:
                    log_text(
                        "LOAD_MODEL_ERROR",
                        f"Error in on_load_complete callback: {cb_error}",
                    )
            log_text(
                "LOAD_MODEL_WORKER",
                f"Worker finished for model: {model_key}, Success: {success}",
            )

    def load_model(self, model_key: str, on_load_complete: callable = None):
        log_text("LOAD_MODEL_TRACE", f"Attempting to load model: {model_key}")
        if not model_key or model_key not in config.AVAILABLE_LLMS:
            self._log_status(f"Invalid model key: '{model_key}'. Cannot load.", "red")
            if on_load_complete:
                on_load_complete(False)
            return False

        model_path = config.AVAILABLE_LLMS[model_key]
        with self._load_lock:
            if self._current_model_name == model_key and self._model is not None:
                self._log_status(f"Model '{model_key}' is already loaded.", "blue")
                if on_load_complete:
                    on_load_complete(True)
                return True

        log_text("LOAD_MODEL", f"Starting background thread to load model: {model_key}")
        thread = threading.Thread(
            target=self._load_model_worker,
            args=(model_key, model_path, on_load_complete),
            daemon=True,
        )
        thread.start()
        return True

    def _on_model_load_complete_for_processing(self, success: bool):
        log_text(
            "LLM_CALLBACK",
            f"_on_model_load_complete_for_processing. Success: {success}",
        )
        pending_req_details = self._pending_request
        self._pending_request = None

        if not pending_req_details:
            log_text(
                "LLM_CALLBACK_WARN",
                "Model load complete, but no pending request found.",
            )
            return

        input_text, mode, custom_prompt, target_model_key = pending_req_details.values()

        if success:
            with self._load_lock:
                if self._current_model_name == target_model_key:
                    log_text(
                        "LLM_CALLBACK",
                        f"Model '{target_model_key}' loaded, starting worker for pending request.",
                    )
                    thread = threading.Thread(
                        target=self._process_text_worker,
                        args=(input_text, mode, custom_prompt, target_model_key),
                        daemon=True,
                    )
                    thread.start()
                else:
                    error_msg = f"Model '{self._current_model_name}' is loaded, but pending request required '{target_model_key}'. Aborting."
                    log_text("LLM_CALLBACK_ERROR", error_msg)
                    self._log_status(error_msg, "red")
                    if self.on_processing_complete:
                        self.on_processing_complete(
                            f"Error: {error_msg}", input_text, mode, 0.0
                        )
        else:
            error_msg = (
                f"Failed to load required model '{target_model_key}' for mode '{mode}'."
            )
            log_text("LLM_CALLBACK_ERROR", error_msg)
            self._log_status(error_msg, "red")
            if self.on_processing_complete:
                self.on_processing_complete(
                    f"Error: {error_msg}", input_text, mode, 0.0
                )

    def process_text(self, input_text: str, mode: str, custom_prompt: str = None):
        log_text(
            "PROCESS_TEXT",
            f"Mode: {mode}, Input: '{input_text[:50]}...' Custom prompt: {custom_prompt is not None}",
        )
        if mode not in ["proofread", "letter"]:
            error_msg = f"Invalid processing mode: {mode}"
            self._log_status(error_msg, "red")
            if self.on_processing_complete:
                self.on_processing_complete(
                    f"Error: {error_msg}", input_text, mode, 0.0
                )
            return

        target_model_id = (
            self._selected_proofing_model_id
            if mode == "proofread"
            else self._selected_letter_model_id
        )
        if not target_model_id:
            error_msg = f"No model selected for mode '{mode}'. Please check settings."
            self._log_status(error_msg, "red")
            if self.on_processing_complete:
                self.on_processing_complete(
                    f"Error: {error_msg}", input_text, mode, 0.0
                )
            return

        target_model_key = next(
            (
                key
                for key, value in config.AVAILABLE_LLMS.items()
                if value == target_model_id
            ),
            None,
        )
        if not target_model_key:
            error_msg = f"Selected model ID '{target_model_id}' for mode '{mode}' not found in config."
            self._log_status(error_msg, "red")
            if self.on_processing_complete:
                self.on_processing_complete(
                    f"Error: {error_msg}", input_text, mode, 0.0
                )
            return

        with self._load_lock:
            model_loaded_correctly = (
                self._current_model_name == target_model_key and self._model is not None
            )

        if model_loaded_correctly:
            log_text(
                "PROCESS_TEXT",
                f"Model '{target_model_key}' already loaded. Starting worker.",
            )
            thread = threading.Thread(
                target=self._process_text_worker,
                args=(input_text, mode, custom_prompt, target_model_key),
                daemon=True,
            )
            thread.start()
        else:
            log_text(
                "PROCESS_TEXT",
                f"Model '{target_model_key}' not loaded. Storing request and initiating load.",
            )
            self._pending_request = {
                "input_text": input_text,
                "mode": mode,
                "custom_prompt": custom_prompt,
                "target_model_key": target_model_key,
            }
            self.load_model(
                target_model_key,
                on_load_complete=self._on_model_load_complete_for_processing,
            )

    def _post_process_response(self, response_text: str, mode: str) -> str:
        """Post-processes the LLM's response based on the mode."""
        return self._professional_formatter.post_process_response(response_text, mode)

    def _process_text_worker(
        self, input_text: str, mode: str, custom_prompt: str, target_model_key: str
    ):
        processing_start_time = time.time()
        final_processed_text = ""
        error_occurred_msg = None
        proofing_activity_signaled_active = False
        log_label = "LLM_PROOFREAD" if mode == "proofread" else "LLM_LETTER"

        try:
            with self._load_lock:
                if (
                    self._current_model_name != target_model_key
                    or not self._model
                    or not self._tokenizer
                ):
                    error_occurred_msg = (
                        f"Model '{target_model_key}' not loaded correctly in worker."
                    )
                    raise RuntimeError(error_occurred_msg)
                current_model, current_tokenizer, current_model_name = (
                    self._model,
                    self._tokenizer,
                    self._current_model_name,
                )

            prompt_template = custom_prompt or (
                self._proofing_prompt if mode == "proofread" else self._letter_prompt
            )

            output_format_instructions = ""
            if mode == "proofread":
                output_format_instructions = (
                    "Your response MUST be structured in two distinct parts:\n\n"
                    "PART 1: YOUR THOUGHT PROCESS (MANDATORY)\n"
                    "First, provide your detailed thought process for proofreading the 'Input Text'. "
                    "This thought process MUST be enclosed entirely within <think> and </think> tags (use EXACTLY these English tags). "
                    "For example: <think>The input text is '...'. I will check for spelling errors in '...' and clarity in the phrase '...'. I will also ensure it meets medical chart standards. My goal is to make it concise and accurate.</think>\n\n"
                    "PART 2: CORRECTED TEXT (MANDATORY)\n"
                    "Immediately after your thought process (i.e., after the closing </think> tag), provide ONLY the corrected version of the 'Input Text'.\n"
                    "- The corrected text MUST be formatted as a bulleted list. Use standard bullet markers like '-'.\n"
                    "- Each bullet point should represent a distinct corrected sentence or a significant, coherent segment of the corrected text.\n"
                    "- DO NOT include any conversational filler, explanations, apologies, or introductory/closing phrases before, between, or after the bullet points in this part. Deliver ONLY the bulleted list of corrections.\n"
                    "- Ensure there is NO text after the final bullet point.\n\n"
                    "COMPLETE OUTPUT EXAMPLE (Follow this structure precisely):\n"
                    "<think>\n"
                    "The input 'Patient complaned of feever and chils for 3 day.' has spelling errors: 'complaned' should be 'complained', 'feever' should be 'fever', 'chils' should be 'chills'. The phrase 'for 3 day' should be 'for 3 days'. The sentence is for a medical chart, so it must be concise and medically accurate. I will correct these specific errors.\n"
                    "</think>\n"
                    "- Patient complained of fever and chills for 3 days.\n"
                )
            elif (
                mode == "letter"
            ):  # Optional: Add specific instructions for letter mode if needed
                output_format_instructions = (
                    "Generate a professional letter based on the input text. Ensure the tone is appropriate for the context implied by the input.\n"
                    "Format the letter with clear paragraphs. Do not add any conversational filler before or after the letter content itself.\n"
                )

            full_prompt = (
                f"{prompt_template}\n\n"
                f"IMPORTANT: You MUST strictly follow these output formatting instructions for your entire response:\n"
                f"{output_format_instructions}\n\n"
                f"-----\n"
                f"Input Text to {mode.capitalize()}:\n{input_text}\n\n"
                f"Now, generate the {mode.capitalize()} Output, adhering to all instructions above:\n"
            )
            # Extract string processing outside f-string to avoid backslash syntax error
            prompt_preview = full_prompt[:250].replace('\n', ' ')
            log_text(
                "LLM_WORKER_PROMPT",
                f"Using model: {current_model_name}, Mode: {mode}, Prompt starts: '{prompt_preview}...' Input length: {len(input_text)}",
            )

            sampler = make_sampler(temp=config.LLM_TEMPERATURE, top_p=config.LLM_TOP_P)

            if self.on_proofing_activity_callback:
                self.on_proofing_activity_callback(True)
                proofing_activity_signaled_active = True

            if self.on_status_update_callback and proofing_activity_signaled_active:
                log_text(
                    f"{log_label}_DEBUG_STREAM_TYPE",
                    f"Sending initial PROOF_STREAM:thinking (should initialize thinking area)",
                )
                self.on_status_update_callback(
                    f"PROOF_STREAM:thinking:Processing with {current_model_name}...",
                    "black",
                )

            # --- NEW: build a ChatML prompt if the tokenizer supports it -------------
            use_chat_template = hasattr(current_tokenizer, "apply_chat_template")
            if use_chat_template:
                # Qwen's template flips the "reasoning" switch when enable_thinking=True
                messages = [
                    {
                        "role": "system",
                        # Keep it short; your detailed rules live in full_prompt ↓
                        "content": "You are a meticulous medical proof-reader.",
                    },
                    {
                        "role": "user",
                        "content": full_prompt,  # ← all your instructions + input text
                    },
                ]
                prompt_for_llm = current_tokenizer.apply_chat_template(
                    messages,
                    add_generation_prompt=True,  # inserts assistant stub
                    enable_thinking=True,  # crucial: restores <think> … </think>
                    tokenize=False,  # we want a raw string
                )
            else:
                prompt_for_llm = full_prompt
            # -------------------------------------------------------------------------

            stream = stream_generate(
                current_model,
                current_tokenizer,
                prompt=prompt_for_llm,
                **self.generation_params,
                sampler=sampler,
            )

            thinking_content_buffer = ""
            response_content_buffer = ""
            in_thinking_block = False
            # Support both English and Chinese thinking tags
            think_tag_open_en = "<think>"
            think_tag_close_en = "</think>"
            think_tag_open_cn = "<思考过程>"
            think_tag_close_cn = "</思考过程>"

            # Track which tag format we're using
            current_think_open = None
            current_think_close = None

            log_text(f"{log_label}_STREAM_START", "Starting to process token stream.")

            for response_obj in stream:
                token_chunk_full_response = response_obj.text
                if not token_chunk_full_response:
                    # log_text(f"{log_label}_DEBUG", "Empty token chunk received from stream, skipping.")
                    continue

                # log_text(f"{log_label}_RAW_CHUNK", f"Raw chunk: '{token_chunk_full_response}'")

                # Check for start of thinking block
                if not in_thinking_block:
                    # Check for English thinking tags first
                    if think_tag_open_en in token_chunk_full_response:
                        parts = token_chunk_full_response.split(think_tag_open_en, 1)
                        current_think_open = think_tag_open_en
                        current_think_close = think_tag_close_en
                        pre_think_content = parts[0]
                        post_think_content = parts[1]

                        if pre_think_content:
                            log_text(
                                f"{log_label}_WARN",
                                f"Unexpected content before {current_think_open}: '{pre_think_content}'. Treating as response.",
                            )
                            response_content_buffer += pre_think_content
                            # Escape newlines for IPC transmission
                            escaped_chunk = pre_think_content.replace(
                                "\n", "\\n"
                            ).replace("\r", "\\r")
                            self._log_status(
                                f"PROOF_STREAM:chunk:{escaped_chunk}", "blue"
                            )

                        in_thinking_block = True
                        log_text(
                            f"{log_label}_DEBUG",
                            f"Entered thinking block (EN). Initial content for thinking: '{post_think_content[:50]}...'",
                        )
                        token_chunk_full_response = post_think_content

                    # Check for Chinese thinking tags if English not found
                    elif think_tag_open_cn in token_chunk_full_response:
                        parts = token_chunk_full_response.split(think_tag_open_cn, 1)
                        current_think_open = think_tag_open_cn
                        current_think_close = think_tag_close_cn
                        pre_think_content = parts[0]
                        post_think_content = parts[1]

                        if pre_think_content:
                            log_text(
                                f"{log_label}_WARN",
                                f"Unexpected content before {current_think_open}: '{pre_think_content}'. Treating as response.",
                            )
                            response_content_buffer += pre_think_content
                            # Escape newlines for IPC transmission
                            escaped_chunk = pre_think_content.replace(
                                "\n", "\\n"
                            ).replace("\r", "\\r")
                            self._log_status(
                                f"PROOF_STREAM:chunk:{escaped_chunk}", "blue"
                            )

                        in_thinking_block = True
                        log_text(
                            f"{log_label}_DEBUG",
                            f"Entered thinking block (CN). Initial content for thinking: '{post_think_content[:50]}...'",
                        )
                        token_chunk_full_response = post_think_content
                    else:
                        # Add debug to see what we're actually getting
                        if (
                            "<" in token_chunk_full_response
                            or ">" in token_chunk_full_response
                        ):
                            print(
                                f"[THINKING_DEBUG] CHUNK WITH BRACKETS (not detected as thinking): {repr(token_chunk_full_response)}"
                            )

                # Check for end of thinking block using the detected tag format
                if (
                    in_thinking_block
                    and current_think_close
                    and current_think_close in token_chunk_full_response
                ):
                    parts = token_chunk_full_response.split(current_think_close, 1)
                    thinking_piece = parts[0]
                    thinking_content_buffer += thinking_piece

                    if thinking_content_buffer.strip():
                        # Escape newlines for IPC transmission
                        escaped_thinking = thinking_content_buffer.replace(
                            "\n", "\\n"
                        ).replace("\r", "\\r")
                        self._log_status(
                            f"PROOF_STREAM:thinking:{escaped_thinking}", "blue"
                        )

                    thinking_content_buffer = ""
                    in_thinking_block = False
                    # Reset the tag tracking
                    current_think_open = None
                    current_think_close = None
                    log_text(f"{log_label}_DEBUG", f"Exited thinking block.")

                    token_chunk_full_response = parts[1]

                    # Clean up any redundant closing tag remnants
                    for close_tag in [think_tag_close_en, think_tag_close_cn]:
                        if token_chunk_full_response.lstrip().startswith(close_tag):
                            log_text(
                                f"{log_label}_WARN",
                                f"Stripping redundant leading '{close_tag}' from response part post-exit.",
                            )
                            idx_strip = token_chunk_full_response.find(close_tag)
                            token_chunk_full_response = token_chunk_full_response[
                                idx_strip + len(close_tag) :
                            ]
                            break

                if in_thinking_block:
                    thinking_content_buffer += token_chunk_full_response
                    if (
                        "\n" in thinking_content_buffer
                        or len(thinking_content_buffer) > 50
                    ):
                        if thinking_content_buffer.strip():
                            # Escape newlines for IPC transmission
                            escaped_thinking = thinking_content_buffer.replace(
                                "\n", "\\n"
                            ).replace("\r", "\\r")
                            self._log_status(
                                f"PROOF_STREAM:thinking:{escaped_thinking}", "blue"
                            )
                            thinking_content_buffer = ""
                else:
                    if token_chunk_full_response:
                        response_content_buffer += token_chunk_full_response

                        # Escape newlines for IPC transmission
                        escaped_chunk = token_chunk_full_response.replace(
                            "\n", "\\n"
                        ).replace("\r", "\\r")
                        self._log_status(f"PROOF_STREAM:chunk:{escaped_chunk}", "blue")

            log_text(f"{log_label}_STREAM_END", "Finished processing token stream.")

            if thinking_content_buffer.strip() and in_thinking_block:
                # Escape newlines for IPC transmission
                escaped_thinking = thinking_content_buffer.replace("\n", "\\n").replace(
                    "\r", "\\r"
                )
                self._log_status(f"PROOF_STREAM:thinking:{escaped_thinking}", "blue")
            elif thinking_content_buffer.strip() and not in_thinking_block:
                log_text(
                    f"{log_label}_WARN",
                    f"Orphaned thinking content after loop but not in_thinking_block: '{thinking_content_buffer[:100]}...' Discarding.",
                )

            raw_llm_output = response_content_buffer

            final_processed_text = self._post_process_response(
                raw_llm_output.strip(), mode
            )

            log_text(
                f"{log_label}_WORKER_FINAL_TEXT",
                f"Final processed text: '{final_processed_text[:200]}...'",
            )

            if not final_processed_text and not error_occurred_msg:
                log_text(
                    f"{log_label}_WORKER_WARN",
                    "LLM generation resulted in effectively empty text after post-processing.",
                )

        except Exception as e_gen:
            error_details = traceback.format_exc()
            error_occurred_msg = f"Error during LLM generation: {e_gen}"
            log_text(
                f"{log_label}_WORKER_ERROR", f"{error_occurred_msg}\n{error_details}"
            )
            final_processed_text = (
                f"Error: {e_gen}"  # Ensure final_processed_text has error for callback
            )
            if self.on_status_update_callback and proofing_activity_signaled_active:
                self.on_status_update_callback(
                    f"PROOF_STREAM:thinking:LLM Error: {str(e_gen).splitlines()[0]}. Please try again.",
                    "red",
                )

        finally:
            processing_duration = time.time() - processing_start_time
            log_text(
                f"{log_label}_WORKER_FINALLY",
                f"Worker finished. Duration: {processing_duration:.2f}s. Error: {error_occurred_msg}",
            )

            if proofing_activity_signaled_active and self.on_status_update_callback:
                try:
                    self.on_status_update_callback(f"PROOF_STREAM:end", "black")
                except Exception as cb_e_status_end:
                    log_text(
                        f"{log_label}_ACTIVITY_ERROR",
                        f"Error sending PROOF_STREAM:end: {cb_e_status_end}",
                    )

            if proofing_activity_signaled_active and self.on_proofing_activity_callback:
                try:
                    self.on_proofing_activity_callback(False)
                    log_text(
                        f"{log_label}_ACTIVITY", "Signaled proofing activity FINISHED"
                    )
                except Exception as cb_e:
                    log_text(
                        f"{log_label}_ACTIVITY_ERROR",
                        f"Error signaling proofing activity finished: {cb_e}",
                    )

            text_for_callback = (
                error_occurred_msg if error_occurred_msg else final_processed_text
            )
            if self.on_processing_complete:
                try:
                    self.on_processing_complete(
                        text_for_callback, input_text, mode, processing_duration
                    )
                except Exception as complete_cb_err:
                    log_text(
                        f"{log_label}_COMPLETE_CB_ERROR",
                        f"Error in on_processing_complete callback: {complete_cb_err}",
                    )

            if error_occurred_msg:
                self._log_status(
                    f"LLM Error ({mode}): {error_occurred_msg.splitlines()[0]}", "red"
                )
                memory_monitor.log_proofing_operation(
                    operation=f"{mode}_error",
                    model_name=target_model_key,
                    input_length=len(input_text),
                    error=error_occurred_msg,
                    duration=processing_duration,
                )
            else:
                self._log_status(
                    f"LLM processing successful ({mode}, {processing_duration:.2f}s).",
                    "green",
                )
                memory_monitor.log_proofing_operation(
                    operation=f"{mode}_complete",
                    model_name=target_model_key,
                    input_length=len(input_text),
                    output_length=len(final_processed_text),
                    duration=processing_duration,
                )

    def update_prompts(self, proofing_prompt: str, letter_prompt: str):
        if proofing_prompt is not None:
            self._proofing_prompt = proofing_prompt
            log_text(
                "LLM_CONFIG", f"Proofing prompt updated to: '{proofing_prompt[:50]}...'"
            )
        if letter_prompt is not None:
            self._letter_prompt = letter_prompt
            log_text(
                "LLM_CONFIG", f"Letter prompt updated to: '{letter_prompt[:50]}...'"
            )
        self._log_status("Prompts updated.", "grey")

    def update_selected_models(self, proofing_model_id: str, letter_model_id: str):
        changed = False
        if proofing_model_id and self._selected_proofing_model_id != proofing_model_id:
            self._selected_proofing_model_id = proofing_model_id
            log_text(
                "LLM_CONFIG", f"Selected proofing model set to ID: {proofing_model_id}"
            )
            changed = True

        if letter_model_id and self._selected_letter_model_id != letter_model_id:
            self._selected_letter_model_id = letter_model_id
            log_text(
                "LLM_CONFIG", f"Selected letter model set to ID: {letter_model_id}"
            )
            changed = True

        if changed:
            self._log_status(
                f"Models updated: Proof='{self._selected_proofing_model_id}', Letter='{self._selected_letter_model_id}'",
                "grey",
            )
        log_text(
            "LLM_CONFIG",
            f"Current models: Proof='{self._selected_proofing_model_id}', Letter='{self._selected_letter_model_id}'",
        )

    def get_available_models_for_electron(self):
        models_list = []
        if hasattr(config, "AVAILABLE_LLMS") and isinstance(
            config.AVAILABLE_LLMS, dict
        ):
            for name, model_id_path in config.AVAILABLE_LLMS.items():
                models_list.append({"id": model_id_path, "name": name})
        else:
            log_text(
                "LLM_CONFIG_ERROR", "config.AVAILABLE_LLMS not found or not a dict."
            )
            models_list.append({"id": "error", "name": "Error: LLMs not configured"})
        return models_list


# Example Usage (for testing purposes)
if __name__ == "__main__":
    print("LLMHandler Test Script Starting...")

    def mock_processing_done(processed_text_or_error, original_text, mode, duration):
        print(f"\n--- MOCK PROCESSING DONE ({mode.upper()}) ---")
        print(f"Duration: {duration:.2f}s")
        print(f"Original: '{original_text}'")
        print(f"Processed/Error: '{processed_text_or_error}'")
        print(f"----------------------------")

    def mock_status_update(message, color):
        # Filter out PROOF_STREAM:response for cleaner test output, show others
        if not message.startswith("PROOF_STREAM:response:"):
            print(f"--- MOCK STATUS [{color.upper()}]: {message} ---")
        elif message.startswith("PROOF_STREAM:response:") and len(message) > 30:
            print(
                f"--- MOCK STATUS [{color.upper()}]: {message[:30]}... (response chunk) ---"
            )

    def mock_proofing_activity(is_active):
        print(
            f"--- MOCK PROOFING ACTIVITY: {'STARTED' if is_active else 'FINISHED'} ---"
        )

    test_handler = LLMHandler(
        on_processing_complete_callback=mock_processing_done,
        on_status_update_callback=mock_status_update,
        on_proofing_activity_callback=mock_proofing_activity,
    )

    print("\n--- Test Case 1: Configuration Updates ---")
    test_handler.update_prompts(
        "Proofread this text carefully: {text}", "Write a formal letter about: {text}"
    )

    first_model_key, first_model_id = None, None
    if hasattr(config, "AVAILABLE_LLMS") and config.AVAILABLE_LLMS:
        first_model_key = list(config.AVAILABLE_LLMS.keys())[0]
        first_model_id = config.AVAILABLE_LLMS[first_model_key]
        print(
            f"Using first available model for testing: Key='{first_model_key}', ID='{first_model_id}'"
        )
        test_handler.update_selected_models(
            proofing_model_id=first_model_id, letter_model_id=first_model_id
        )
    else:
        print(
            "WARNING: config.AVAILABLE_LLMS is empty. Processing tests will likely fail to load models."
        )
        # Set dummy IDs if no real models are configured to allow basic handler operation tests
        test_handler.update_selected_models(
            proofing_model_id="dummy/proof-model", letter_model_id="dummy/letter-model"
        )

    print(
        f"Available models for Electron: {test_handler.get_available_models_for_electron()}"
    )

    if not first_model_key:  # Check if a real model key was found
        print(
            "\nSKIPPING MODEL LOADING & PROCESSING TESTS as no model key could be determined from config."
        )
    else:
        print(
            f"\n--- Test Case 2: Loading Model '{first_model_key}' (ID: {first_model_id}) ---"
        )

        load_event = threading.Event()

        def on_test_load_complete(success):
            print(f"--- MOCK LOAD COMPLETE: {'Success' if success else 'Failure'} ---")
            load_event.set()  # Signal that loading (or attempt) has finished

        test_handler.load_model(first_model_key, on_load_complete=on_test_load_complete)
        print("Waiting for model load to complete...")
        load_event.wait(timeout=60)  # Wait for up to 60 seconds for the model to load

        if not test_handler._model:  # Check if model actually loaded
            print(
                f"Model '{first_model_key}' did not load successfully. Skipping further processing tests."
            )
        else:
            print("\n--- Test Case 3: Proofread Text (with <think> tags expected) --- ")
            text_to_proofread = (
                "Patient states they hav a sore throte and hedache. Temp is 99.9F."
            )
            # Ensure the default proofread prompt is used (which includes the <think> tag instructions)
            test_handler.update_prompts(
                config.DEFAULT_PROOFREAD_PROMPT, test_handler._letter_prompt
            )
            test_handler.process_text(text_to_proofread, "proofread")
            time.sleep(25)  # Allow ample time for streaming and processing

            print(
                "\n--- Test Case 4: Generate Letter (no <think> tags expected in final output) --- "
            )
            text_for_letter = "Regarding the upcoming conference, please arrange travel and accommodation for Dr. Smith."
            test_handler.process_text(
                text_for_letter,
                "letter",
                custom_prompt="Compose a brief memo based on this: {text}",
            )
            time.sleep(25)  # Allow time for processing

    print("\n--- Test Case 5: Invalid Mode --- ")
    test_handler.process_text("some text", "summary_mode")  # This mode is invalid
    time.sleep(2)

    print("\n--- Test Case 6: Process with No Model Selected (Proofread) --- ")
    original_proof_id = test_handler._selected_proofing_model_id
    test_handler.update_selected_models(
        proofing_model_id=None, letter_model_id=test_handler._selected_letter_model_id
    )
    test_handler.process_text("another test for proofreading", "proofread")
    test_handler.update_selected_models(
        proofing_model_id=original_proof_id,
        letter_model_id=test_handler._selected_letter_model_id,
    )  # Restore
    time.sleep(2)

    print("\nLLM Handler test script finished.")
