"""Alexa Skills Kit Lambda adapter for ResQ-AI's read-only safety guidance.

This standard Alexa custom skill is separate from the Alexa+ MCP server. It provides
general safety guidance only; it does not read live incidents or dispatch resources.
"""
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import is_request_type, is_intent_name

sb = SkillBuilder()

RESPONSES = {
    "EarthquakeSafetyIntent": (
        "During shaking, drop, cover, and hold on. Protect your head and neck, "
        "stay away from windows, and do not use elevators. Outdoors, move away "
        "from buildings and power lines. After shaking, expect aftershocks and "
        "avoid damaged buildings. Follow local authorities. This is general "
        "guidance, not a live local warning. For official information, visit U S G S dot gov."
    ),
    "FloodSafetyIntent": (
        "Move to higher ground early if flooding threatens and follow official evacuation orders. "
        "Never walk, swim, or drive through floodwater. Keep away from drains, riverbanks, and fallen "
        "power lines. ResQ cannot verify current road conditions or shelter capacity. "
        "Check official local alerts."
    ),
    "CycloneSafetyIntent": (
        "Follow official cyclone warnings and evacuate when instructed. Shelter in a sturdy building "
        "away from windows. Avoid beaches, flood-prone areas, and downed wires. Check the India "
        "Meteorological Department and local authority updates for current warnings."
    ),
    "FireSafetyIntent": (
        "Leave a burning building immediately using the safest exit, stay low under smoke, and do not "
        "use elevators. Once outside, stay outside and call local emergency services. Do not re-enter."
    ),
    "HeatSafetyIntent": (
        "During extreme heat, move to a cool place, reduce exertion, and drink water if you can safely "
        "swallow. Check on vulnerable people. Confusion, fainting, or seizures can be an emergency; "
        "seek urgent medical help and follow dispatcher instructions."
    ),
    "PreparednessIntent": (
        "Prepare drinking water, essential medicines, a first-aid kit, a torch, batteries or a power bank, "
        "important documents, and emergency contacts. Plan a family meeting point and know official "
        "evacuation routes and designated shelters before an emergency."
    ),
    "EmergencyHelpIntent": (
        "If someone is in immediate danger, contact local emergency services now. In India, 1 1 2 is "
        "the pan-India emergency response number. If you are elsewhere, use your local emergency number. "
        "ResQ cannot call responders or dispatch resources."
    ),
}

def _say(handler_input, text, end_session=False):
    builder = handler_input.response_builder.speak(text).set_should_end_session(end_session)
    return builder.response

@sb.request_handler(can_handle_func=is_request_type("LaunchRequest"))
def launch_handler(handler_input):
    return _say(
        handler_input,
        "Welcome to ResQ Assistant. You can ask for earthquake safety, flood safety, "
        "cyclone safety, fire safety, heat safety, emergency preparedness, or emergency help. "
        "I provide general guidance, not live warnings or dispatch.",
    )

@sb.request_handler(can_handle_func=lambda h: is_request_type("IntentRequest")(h) and
                    h.request_envelope.request.intent.name in RESPONSES)
def safety_intent_handler(handler_input):
    name = handler_input.request_envelope.request.intent.name
    return _say(handler_input, RESPONSES[name])

@sb.request_handler(can_handle_func=is_intent_name("AMAZON.HelpIntent"))
def help_handler(handler_input):
    return _say(
        handler_input,
        "Ask about earthquake, flood, cyclone, fire, heat, preparedness, or emergency help. "
        "For immediate danger, contact local emergency services.",
    )

@sb.request_handler(can_handle_func=lambda h: is_intent_name("AMAZON.CancelIntent")(h) or
                    is_intent_name("AMAZON.StopIntent")(h))
def stop_handler(handler_input):
    return _say(handler_input, "Stay safe. ResQ Assistant is ending this session.", True)

@sb.request_handler(can_handle_func=is_request_type("SessionEndedRequest"))
def session_ended_handler(handler_input):
    return handler_input.response_builder.response

@sb.exception_handler(can_handle_func=lambda _i, _e: True)
def error_handler(handler_input, _exception):
    return _say(
        handler_input,
        "Sorry, ResQ Assistant could not process that request. For an active emergency, contact local emergency services.",
        True,
    )

handler = sb.lambda_handler()
