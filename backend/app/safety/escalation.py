"""Escalation policy, response templates and the verified support directory.

Policy (most severe category wins):

=====================  =========  ===============================================
Category               Level      Behaviour
=====================  =========  ===============================================
immediate_danger       urgent     Deterministic safety message; no generation.
self_harm              urgent     Deterministic supportive message; no generation.
surveillance_request   declined   Deterministic decline + constructive redirect.
manipulation_request   declined   Deterministic decline + constructive redirect.
physical_violence      support    Generate with safety constraints + resources.
sexual_coercion        support    Generate with safety constraints + resources.
threats                support    Generate with safety constraints + resources.
stalking               support    Generate with safety constraints + resources.
coercive_control       caution    Generate carefully; ask a gentle clarifying question.
repeated_humiliation   caution    Generate carefully; ask a gentle clarifying question.
(none)                 none       Ordinary flow.
=====================  =========  ===============================================

Templates never contain telephone numbers. Numbers come only from
``data/metadata/support_directory.json`` and only for the region the user selected.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.schemas import SafetyLevel, SupportResource
from app.safety.classifier import Assessment
from app.safety.rules import RiskCategory

C = RiskCategory
PRIORITY: list[tuple[RiskCategory, SafetyLevel]] = [
    (C.IMMEDIATE_DANGER, SafetyLevel.URGENT),
    (C.SELF_HARM, SafetyLevel.URGENT),
    (C.SURVEILLANCE_REQUEST, SafetyLevel.DECLINED),
    (C.MANIPULATION_REQUEST, SafetyLevel.DECLINED),
    (C.PHYSICAL_VIOLENCE, SafetyLevel.SUPPORT),
    (C.SEXUAL_COERCION, SafetyLevel.SUPPORT),
    (C.THREATS, SafetyLevel.SUPPORT),
    (C.STALKING, SafetyLevel.SUPPORT),
    (C.COERCIVE_CONTROL, SafetyLevel.CAUTION),
    (C.REPEATED_HUMILIATION, SafetyLevel.CAUTION),
]

LEVEL_RANK = {
    SafetyLevel.NONE: 0,
    SafetyLevel.CAUTION: 1,
    SafetyLevel.SUPPORT: 2,
    SafetyLevel.DECLINED: 3,
    SafetyLevel.URGENT: 4,
}


@dataclass(slots=True)
class SafetyDecision:
    level: SafetyLevel
    primary: RiskCategory | None
    categories: list[RiskCategory]
    skip_generation: bool
    template: str | None
    banner: str | None
    prompt_addendum: str | None


# --------------------------------------------------------------------------- templates

TEMPLATES: dict[str, dict[str, str]] = {
    "immediate_danger": {
        "en": (
            "I'm really concerned for your safety right now.\n\n"
            "**If you are in immediate danger, please contact your local emergency number or get to a place "
            "where other people are around.** If you can, reach out to someone you trust and tell them where you are.\n\n"
            "I'm a chatbot running on this device — I can't call anyone, see where you are, or send help. "
            "When you are somewhere safe, I'm here to talk through what happened and what options you have."
        ),
        "bn": (
            "এই মুহূর্তে আপনার নিরাপত্তা নিয়ে আমি সত্যিই চিন্তিত।\n\n"
            "**আপনি যদি এখনই বিপদে থাকেন, দয়া করে আপনার এলাকার জরুরি নম্বরে যোগাযোগ করুন অথবা এমন জায়গায় যান যেখানে অন্য মানুষ আছে।** "
            "সম্ভব হলে বিশ্বস্ত কাউকে জানান আপনি কোথায় আছেন।\n\n"
            "আমি এই ডিভাইসে চলা একটি চ্যাটবট — আমি কাউকে ফোন করতে, আপনার অবস্থান জানতে বা সাহায্য পাঠাতে পারি না। "
            "আপনি নিরাপদ জায়গায় পৌঁছালে, কী হয়েছে আর আপনার সামনে কী কী পথ আছে তা নিয়ে আমরা কথা বলতে পারি।"
        ),
        "banglish": (
            "Ei muhurte apnar nirapotta niye ami shotti chintito.\n\n"
            "**Apni jodi ekhon e bipode thaken, please apnar elakar emergency number e jogajog korun ba emon jaygay jan "
            "jekhane onno manush ache.** Shombhob hole bishwosto karo ke janan apni kothay achen.\n\n"
            "Ami ei device e chola ekta chatbot — ami kauke call korte, apnar location jante ba help pathate pari na. "
            "Apni nirapod jaygay pouchale, ki hoyeche ar apnar shamne ki ki path ache ta niye amra kotha bolte pari."
        ),
    },
    "self_harm": {
        "en": (
            "Thank you for telling me. It sounds like you're carrying something really heavy right now, and I'm glad you said it out loud.\n\n"
            "**If you might act on these thoughts or you're not safe right now, please contact your local emergency number "
            "or a crisis line, or ask someone near you to stay with you.** You don't have to handle this moment alone.\n\n"
            "I'm a chatbot, not a crisis service, and I can't contact anyone for you. If you'd like, you can tell me a bit "
            "more about what's been happening — I'll listen."
        ),
        "bn": (
            "আমাকে জানানোর জন্য ধন্যবাদ। মনে হচ্ছে আপনি এখন খুব ভারী কিছু বয়ে বেড়াচ্ছেন, আর আপনি যে কথাটা বলেছেন তা গুরুত্বপূর্ণ।\n\n"
            "**আপনি যদি এই চিন্তা অনুযায়ী কিছু করে ফেলার ঝুঁকিতে থাকেন বা এখন নিরাপদ না থাকেন, দয়া করে আপনার এলাকার জরুরি নম্বরে বা কোনো সংকট সহায়তা লাইনে যোগাযোগ করুন, "
            "অথবা কাছের কাউকে আপনার পাশে থাকতে বলুন।** এই মুহূর্তটা আপনাকে একা সামলাতে হবে না।\n\n"
            "আমি একটি চ্যাটবট, সংকট সহায়তা সেবা নই, এবং আমি আপনার হয়ে কাউকে যোগাযোগ করতে পারি না। চাইলে কী হচ্ছে তা আমাকে আরেকটু বলতে পারেন — আমি শুনব।"
        ),
        "banglish": (
            "Amake jananor jonno dhonnobad. Mone hocche apni ekhon khub bhari kichu boye beracchen, ar apni je kotha ta bolechen ta important.\n\n"
            "**Apni jodi ei chinta onujayi kichu kore felar jhuki te thaken ba ekhon nirapod na thaken, please apnar elakar emergency number "
            "ba kono crisis helpline e jogajog korun, othoba kacher kauke apnar pashe thakte bolun.** Ei muhurto ta apnake eka shamlate hobe na.\n\n"
            "Ami ekta chatbot, crisis service na, ar ami apnar hoye kauke contact korte pari na. Chaile ki hocche ta amake ar ektu bolte paren — ami shunbo."
        ),
    },
    "surveillance_request": {
        "en": (
            "I can't help with secretly checking, tracking, or accessing a partner's phone, messages, accounts, or location. "
            "Monitoring someone without their consent tends to damage trust further, and in many places it is illegal.\n\n"
            "What I can help with is the worry underneath it. Suspicion usually comes from something real — a change you've noticed, "
            "a past hurt, or a feeling of distance. If you'd like, tell me what has made you feel this way, and we can think about "
            "how to raise it with your partner directly, or how to decide what you need if you can't trust them."
        ),
        "bn": (
            "সঙ্গীর ফোন, মেসেজ, অ্যাকাউন্ট বা লোকেশন গোপনে দেখা, ট্র্যাক করা বা হ্যাক করার বিষয়ে আমি সাহায্য করতে পারি না। "
            "কারও অনুমতি ছাড়া নজরদারি করলে বিশ্বাস আরও ভাঙে, আর অনেক জায়গায় এটা আইনত অপরাধ।\n\n"
            "তবে এর পেছনের দুশ্চিন্তা নিয়ে আমি সাহায্য করতে পারি। সন্দেহ সাধারণত কোনো বাস্তব কারণ থেকে আসে — কোনো পরিবর্তন, পুরনো কষ্ট, বা দূরত্বের অনুভূতি। "
            "চাইলে বলুন কী দেখে আপনার এমন মনে হচ্ছে, আমরা ভাবতে পারি কীভাবে সরাসরি সঙ্গীর সঙ্গে কথা বলা যায়, বা বিশ্বাস না থাকলে আপনার কী প্রয়োজন।"
        ),
        "banglish": (
            "Partner er phone, message, account ba location lukiye dekha, track kora ba hack korar byapare ami help korte pari na. "
            "Karo permission chara nojordari korle bisshash aro bhange, ar onek jaygay eta illegal.\n\n"
            "Tobe er pichoner dushchinta niye ami help korte pari. Sondeh shadharonoto kono real karon theke ashe — kono poriborton, purono kosto, ba durotter feeling. "
            "Chaile bolun ki dekhe apnar emon mone hocche, amra bhabte pari kivabe shorashori partner er sathe kotha bola jay."
        ),
    },
    "manipulation_request": {
        "en": (
            "I can't help with manipulating, threatening, punishing, or getting revenge on someone, or with sharing private images of them. "
            "Those approaches cause real harm, and some of them are crimes.\n\n"
            "It sounds like you may be feeling hurt, angry, or powerless right now — those feelings make sense and are worth taking seriously. "
            "If you tell me what happened, I can help you think about how to express what you need honestly, set a boundary, "
            "or decide whether this relationship is right for you."
        ),
        "bn": (
            "কাউকে ম্যানিপুলেট করা, হুমকি দেওয়া, শাস্তি দেওয়া, প্রতিশোধ নেওয়া, বা তার ব্যক্তিগত ছবি ছড়ানোর বিষয়ে আমি সাহায্য করতে পারি না। "
            "এগুলো সত্যিকারের ক্ষতি করে, আর এর কিছু অপরাধও।\n\n"
            "মনে হচ্ছে আপনি হয়তো এখন কষ্ট, রাগ বা অসহায়ত্ব অনুভব করছেন — এই অনুভূতিগুলো বোধগম্য এবং গুরুত্বপূর্ণ। "
            "কী হয়েছে বললে, আপনার প্রয়োজন সৎভাবে প্রকাশ করা, সীমা ঠিক করা, বা সম্পর্কটা আপনার জন্য ঠিক কি না তা ভাবতে আমি সাহায্য করতে পারি।"
        ),
        "banglish": (
            "Kauke manipulate kora, humki deya, shasti deya, protishodh neya, ba tar private chobi chorano niye ami help korte pari na. "
            "Egulo shotti kharap khoti kore, ar kichu to oporadh.\n\n"
            "Mone hocche apni hoyto ekhon kosto, rag ba oshohay feel korchen — ei feeling gulo bojha jay ar important. "
            "Ki hoyeche bolle, apnar dorkar ta honest bhabe bola, boundary set kora, ba somporko ta apnar jonno thik kina ta bhabte ami help korte pari."
        ),
    },
}

BANNERS: dict[SafetyLevel, dict[str, str]] = {
    SafetyLevel.SUPPORT: {
        "en": "Your safety matters. If you are ever in immediate danger, contact your local emergency number.",
        "bn": "আপনার নিরাপত্তা গুরুত্বপূর্ণ। কখনো তাৎক্ষণিক বিপদে পড়লে আপনার এলাকার জরুরি নম্বরে যোগাযোগ করুন।",
        "banglish": "Apnar nirapotta important. Kokhono immediate bipode porle apnar elakar emergency number e jogajog korun.",
    },
    SafetyLevel.CAUTION: {
        "en": "Some of what you describe can be part of a controlling pattern. You deserve to feel safe and respected.",
        "bn": "আপনি যা বলছেন তার কিছু নিয়ন্ত্রণমূলক আচরণের অংশ হতে পারে। নিরাপদ ও সম্মানিত বোধ করা আপনার অধিকার।",
        "banglish": "Apni ja bolchen tar kichu controlling behaviour er ongsho hote pare. Nirapod ar shommanito feel kora apnar odhikar.",
    },
    SafetyLevel.URGENT: {
        "en": "If you are in danger right now, contact your local emergency number.",
        "bn": "এখনই বিপদে থাকলে আপনার এলাকার জরুরি নম্বরে যোগাযোগ করুন।",
        "banglish": "Ekhon e bipode thakle apnar elakar emergency number e jogajog korun.",
    },
}

# Recorded in PROMPT_VERSION. safety_v2 (2026-10-15): forbid explanations that excuse or soften the behaviour,
# after both local models offered "he may be protecting you"-style interpretations at caution/support level.
SAFETY_ADDENDA_VERSION = "safety_v2"
_NO_EXCUSES = (
    " Do NOT offer explanations that excuse, justify or soften the partner's behaviour (such as love, worry, "
    "protection, insecurity, stress or anger); the usual 'offer several interpretations' guidance does not apply here."
)

ADDENDA: dict[SafetyLevel, str] = {
    SafetyLevel.SUPPORT: (
        "SAFETY CONTEXT: The user has described possible violence, sexual coercion, threats, or stalking. "
        "Prioritise their safety and autonomy. Believe them and do not minimise. Do NOT suggest confronting the partner, "
        "do NOT suggest couples counselling or joint sessions, and do NOT encourage reconciliation. Do not diagnose anyone. "
        "Mention that specialised domestic-violence support services can help with safety planning, without inventing "
        "names or phone numbers. Keep any practical steps discreet and safe (e.g. a trusted person, a safe place). "
        "If they are in immediate danger they should contact their local emergency number." + _NO_EXCUSES
    ),
    SafetyLevel.CAUTION: (
        "SAFETY CONTEXT: The user described behaviour that may be part of a controlling or demeaning pattern, but the "
        "context is incomplete. Take it seriously without labelling the relationship as abusive. Gently ask one clarifying "
        "question about whether they feel afraid or unsafe. Do not suggest confronting the partner in a way that could "
        "increase risk, and do not recommend couples counselling until safety is clear." + _NO_EXCUSES
    ),
}


# Used when only the semantic (embedding) classifier flagged a risk. Its precision is lower than
# the rules', so the response is proportionate: take it seriously and check in gently, without
# switching to an urgent template. A false alarm then costs one careful question.
SEMANTIC_ADDENDA: dict[RiskCategory, str] = {
    C.SELF_HARM: (
        "SAFETY CONTEXT: The message may express hopelessness or thoughts of self-harm, said indirectly. "
        "Respond warmly first. Gently and directly ask whether they are thinking about harming themselves or "
        "ending their life. Say that if they are in danger or might act on such thoughts, they should contact "
        "their local emergency number or a crisis line, or someone near them, now. Do not give relationship "
        "advice before acknowledging this. Do not invent phone numbers."
    ),
    # Added 2026-10-15: indirect injury descriptions were being answered as questions about appearance.
    C.PHYSICAL_VIOLENCE: (
        "SAFETY CONTEXT: The message may indirectly describe physical harm — for example hiding marks, bruises or "
        "injuries. Do not treat it as a question about appearance, privacy or self-confidence. Respond warmly, then "
        "gently and directly ask whether someone has hurt them and whether they are safe now. Do NOT suggest asking "
        "or confronting the partner about it, and do not suggest joint counselling. Mention that specialised "
        "domestic-violence support services and trusted people can help, without inventing names or phone numbers, "
        "and that in immediate danger they should contact their local emergency number." + _NO_EXCUSES
    ),
}
SEMANTIC_DEFAULT_ADDENDUM = (
    "SAFETY CONTEXT: The message may indirectly describe harm, fear, control, threats or being followed. "
    "Do not assume it is ordinary conflict and do not label the relationship. Take it seriously, gently ask "
    "whether they feel safe, and avoid advice to confront the partner or attend joint counselling until "
    "safety is clear." + _NO_EXCUSES
)


def decide(assessment: Assessment, language: str) -> SafetyDecision:
    lang = language if language in {"en", "bn", "banglish"} else "en"
    categories = [c for c, _ in PRIORITY if c in assessment.categories]
    if not categories:
        return SafetyDecision(SafetyLevel.NONE, None, [], False, None, None, None)
    confirmed = [c for c in categories if not assessment.semantic_only(c)]
    if not confirmed:
        primary = categories[0]
        addendum = SEMANTIC_ADDENDA.get(primary, SEMANTIC_DEFAULT_ADDENDUM)
        banner = BANNERS[SafetyLevel.CAUTION if primary != C.SELF_HARM else SafetyLevel.URGENT].get(lang)
        return SafetyDecision(SafetyLevel.CAUTION, primary, categories, False, None, banner, addendum)
    primary = confirmed[0]
    level = dict(PRIORITY)[primary]
    template = TEMPLATES.get(primary.value, {}).get(lang)
    skip = level in {SafetyLevel.URGENT, SafetyLevel.DECLINED}
    banner = BANNERS.get(level, {}).get(lang)
    return SafetyDecision(level, primary, categories, skip, template if skip else None, banner, ADDENDA.get(level))


def merge_levels(current: SafetyDecision, previous_level: SafetyLevel | None) -> SafetyDecision:
    """Keep conversation-level awareness: a disclosed risk earlier in the conversation keeps at
    least ``support``/``caution`` constraints on later turns even if the new message is benign."""
    if (
        previous_level in {SafetyLevel.SUPPORT, SafetyLevel.URGENT}
        and LEVEL_RANK[current.level] < LEVEL_RANK[SafetyLevel.SUPPORT]
    ):
        current.level = SafetyLevel.SUPPORT
        current.prompt_addendum = ADDENDA[SafetyLevel.SUPPORT]
    elif previous_level == SafetyLevel.CAUTION and current.level == SafetyLevel.NONE:
        current.level = SafetyLevel.CAUTION
        current.prompt_addendum = ADDENDA[SafetyLevel.CAUTION]
    return current


# --------------------------------------------------------------------------- support directory


@lru_cache(maxsize=4)
def load_directory(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"regions": {}}


def resources_for(directory: dict, region: str | None, categories: list[RiskCategory]) -> list[SupportResource]:
    if not region or region == "unspecified":
        return []
    entries = directory.get("regions", {}).get(region, {}).get("resources", [])
    wanted = {c.value for c in categories}
    region_label = directory.get("regions", {}).get(region, {}).get("label", region)
    out = []
    for entry in entries:
        if wanted & set(entry.get("categories", [])):
            out.append(
                SupportResource(
                    name=entry["name"],
                    description=entry["description"],
                    contact=entry.get("contact"),
                    url=entry.get("url"),
                    region=region_label,
                    verified_on=entry["verified_on"],
                    source_url=entry["source_url"],
                )
            )
    return out


def allowed_numbers(directory: dict) -> set[str]:
    numbers = set()
    for region in directory.get("regions", {}).values():
        for entry in region.get("resources", []):
            if entry.get("contact"):
                numbers.add("".join(ch for ch in entry["contact"] if ch.isdigit()))
    return numbers
