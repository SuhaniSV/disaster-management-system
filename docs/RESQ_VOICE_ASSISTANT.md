# ResQ Voice — Alexa+ track web simulation

ResQ Voice is the voice-first web demo surface for the Alexa+ hackathon track. Start a conversation once, speak questions, hear answers automatically, continue with follow-ups, and use **Interrupt / ask now** to stop the current spoken answer.

## Run it

1. Install dependencies and launch the app: `pip install -r requirements.txt`, then `streamlit run app.py`.
2. Open **ResQ Assistant** in the Streamlit navigation.
3. Use a recent Chrome or Edge browser, allow microphone access, and click **Start conversation**.
4. Ask a general question such as "What should I do during an earthquake?" or an operational question such as "Which incident is most urgent?" or "Which shelters have space?".
5. Keep speaking after each answer; click **Interrupt / ask now** to stop speech and ask a follow-up. Click **End conversation** when finished.

## How it works

- Browser speech recognition turns spoken input into text.
- The transcript goes through the existing ResQ Assistant response pipeline.
- Deterministic safety guidance and the existing LLM client (when configured) answer general questions and questions grounded in the current command-center snapshot. A deterministic fallback remains available without an LLM key.
- Answers are spoken automatically using browser speech synthesis. Voice options depend on the browser and operating system.
- The separate self-hosted MCP server remains the Alexa+ track's tool surface. Run it separately with `python -m resq_mcp.server` to demonstrate the read-only incident, priority, resource, shelter, briefing, and configured government-alert tools over Streamable HTTP.

## Important distinction

This is a **simulated Alexa+-style web experience** for the hackathon, not Amazon's actual Alexa voice engine, an Echo-device integration, or an authenticated Alexa+ account link. It provides hands-free turn-taking and a manual interruption control; browser speech recognition/synthesis is not full-duplex streaming speech-to-speech.

## Safety and data integrity

Operational answers use the app's current command-center records. Those records can be simulated or incomplete and may differ from the separate MCP server's demo snapshot. The voice UI is read-only: it does not dispatch responders, call emergency services, or change incident priorities. For immediate danger, contact local emergency services and follow official instructions. Never commit API keys or AWS credentials.
