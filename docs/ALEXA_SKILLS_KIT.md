# ResQ-AI Alexa Skills Kit integration

This repository contains two distinct Alexa-related artifacts:

- **Alexa+ hackathon track:** the existing read-only MCP server documented in [ALEXA_PLUS_HACKATHON.md](ALEXA_PLUS_HACKATHON.md). Direct Alexa+ connection still requires an eligible Alexa+ integration path, a publicly reachable HTTPS endpoint, and any required authentication/account linking.
- **Alexa custom skill:** the AWS Lambda / Alexa Skills Kit (ASK) voice adapter in `alexa/lambda_function.py`. It provides general disaster safety guidance by voice. It is not a direct Alexa+ MCP client and does not query live ResQ incidents, shelter capacity, road conditions, or government alerts.

## Create and test the custom skill

1. Sign in to the [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask) and create a **Custom** skill named ResQ Assistant.
2. Set the invocation name to **rescue assistant**.
3. In the skill's JSON Editor, paste the contents of `alexa/interaction_model.json`, save, and build the model.
4. Create an AWS Lambda function using a Python runtime supported by ASK, with the handler set to `lambda_function.handler`.
5. Install the isolated dependency from `alexa/requirements.txt` into the Lambda deployment package, along with `alexa/lambda_function.py` as the top-level `lambda_function.py`. Alternatively, use the Alexa-hosted custom-skill workflow and adapt the package layout to its editor.
6. Add the Alexa Skills Kit trigger to Lambda and restrict it to your skill ID. In the Developer Console, configure the Lambda ARN as the skill endpoint.
7. Enable **Test** for the development stage and use the Alexa simulator to try:
   - “Alexa, open rescue assistant”
   - “Ask rescue assistant for earthquake safety”
   - “Ask rescue assistant about flood safety”
   - “Ask rescue assistant for emergency help”
8. Review the spoken responses and run the unit tests in this repository before a demo.

Official setup reference: [Develop your first skill with the ASK SDK for Python](https://developer.amazon.com/en-US/docs/alexa/alexa-skills-kit-sdk-for-python/develop-your-first-skill.html).

## Voice safety and limitations

- Answers are general preparedness guidance, not location-aware advice, diagnosis, or live warnings.
- The skill does not dispatch responders, place emergency calls, verify shelter capacity, or provide verified routes.
- For an active emergency, tell the user to contact local emergency services. The India 112 reference applies to India only.
- Do not claim this custom skill is connected to Alexa+ or published in the Alexa Skills Store until those steps are completed and verified.
- Never include AWS credentials, skill secrets, or account identifiers in source control.

## Local checks

The Lambda handler requires `ask-sdk-core`; install it in an isolated environment using:

```bash
python -m pip install -r alexa/requirements.txt
```

The Streamlit app's normal dependencies are unchanged.
