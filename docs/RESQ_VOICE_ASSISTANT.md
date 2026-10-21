# ResQ Assistant browser voice mode

The ResQ Assistant page includes an optional browser voice interface. It uses the browser's Web Speech API to recognize spoken questions and to read answers aloud. The recognized text is passed into the same `answer_question` logic as typed chat, so the assistant continues to use the current command-center snapshot and its existing deterministic fallback.

## Try it

1. Deploy the repository through Streamlit Community Cloud, or run it locally with `streamlit run app.py`.
2. Open **ResQ Assistant** from the app navigation.
3. In **Talk to ResQ Assistant**, choose **Start speaking** and allow microphone access.
4. Ask a supported question, for example “Which incident is most urgent?” or “Which shelters have space?”
5. Read the response in the chat. To hear it aloud, press **Speak answer**.

Use a current browser that supports the Web Speech API (typically Chrome or Edge). Browser support and microphone permissions vary. If speech recognition is unavailable, the regular text chat remains available.

## Scope and safety

- This is a browser-based voice demo for the Alexa-related hackathon work; it is **not** an official Amazon Alexa device connection or direct Alexa+ account link.
- Speech recognition runs through the browser's Web Speech API. Browser implementation and privacy behavior may vary by browser.
- Voice questions use the same ResQ Assistant logic and do not call the separate MCP server directly.
- Incident/resource records may be simulated or incomplete. The assistant cannot call emergency services, dispatch responders, verify capacity, or authorize operational actions.
- For direct Alexa+ MCP testing, follow [ALEXA_PLUS_HACKATHON.md](ALEXA_PLUS_HACKATHON.md). A public Alexa+ connection still requires an eligible endpoint, HTTPS, and the required authentication/account-linking configuration.
