"""Deterministic safety patterns for English, Bangla and Banglish.

Patterns are deliberately conservative: they target clear statements of risk, not words
that merely co-occur with ordinary arguments ("fight", "angry", "shout" alone never
trigger escalation). Every category has test cases in all three languages in
``backend/tests/test_safety.py``.

Patterns are evaluated against lower-cased, NFC-normalized text. Bangla negation follows
the verb (e.g. "মারে না" = "does not hit"), so a short window *after* each match is
checked as well as the window before it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class RiskCategory(StrEnum):
    IMMEDIATE_DANGER = "immediate_danger"
    SELF_HARM = "self_harm"
    PHYSICAL_VIOLENCE = "physical_violence"
    SEXUAL_COERCION = "sexual_coercion"
    THREATS = "threats"
    STALKING = "stalking"
    COERCIVE_CONTROL = "coercive_control"
    REPEATED_HUMILIATION = "repeated_humiliation"
    SURVEILLANCE_REQUEST = "surveillance_request"
    MANIPULATION_REQUEST = "manipulation_request"


@dataclass(frozen=True, slots=True)
class Rule:
    category: RiskCategory
    pattern: re.Pattern[str]
    weight: float = 1.0
    negatable: bool = True
    language: str = "en"


def _r(category: RiskCategory, regex: str, *, weight: float = 1.0, negatable: bool = True, language: str = "en") -> Rule:
    return Rule(category, re.compile(regex, re.IGNORECASE), weight, negatable, language)


# Shared fragments ---------------------------------------------------------------------
PARTNER = r"\b(?:he|she|they|my (?:partner|husband|wife|boyfriend|girlfriend|bf|gf|fianc[ée]e?|spouse|ex))"
BN_PARTNER = r"(?:সে|ও|স্বামী|স্ত্রী|বউ|বর|প্রেমিক|প্রেমিকা|পার্টনার)"

R = RiskCategory
RULES: tuple[Rule, ...] = (
    # ---------------------------------------------------------------- immediate danger
    _r(R.IMMEDIATE_DANGER, r"\b(?:right now|now|tonight)\b.{0,40}\b(?:hitting|beating|attacking|choking|strangling|trying to kill|going to kill|has a (?:knife|gun|weapon))\b", negatable=False),
    _r(R.IMMEDIATE_DANGER, r"\b(?:he|she|they)(?:'s| is| are)\b.{0,25}\b(?:outside|at) (?:my|the) (?:door|house|room)\b.{0,40}\b(?:knife|gun|weapon|kill|hurt)", negatable=False),
    _r(R.IMMEDIATE_DANGER, r"\b(?:i(?:'m| am) )?(?:scared|afraid|terrified) (?:that )?(?:he|she|they)(?:'s| is| are| will| (?:is|are) going to)\b.{0,15}\b(?:kill|murder)\b", negatable=False),
    _r(R.IMMEDIATE_DANGER, r"\b(?:locked me in|won't let me leave the (?:room|house))\b.{0,40}\b(?:hit|hurt|kill|weapon|knife)", negatable=False),
    _r(R.IMMEDIATE_DANGER, r"\bhelp me\b.{0,20}\b(?:he|she|they)(?:'s| is| are)\b.{0,20}\b(?:hitting|hurting|attacking)\b", negatable=False),
    _r(R.IMMEDIATE_DANGER, r"(?:এখনই|এখন|আজ রাতে).{0,30}(?:মেরে ফেলবে|মারছে|মারধর করছে|ছুরি|বন্দুক|গলা চেপে)", negatable=False, language="bn"),
    _r(R.IMMEDIATE_DANGER, r"(?:আমাকে )?মেরে ফেলবে বলে.{0,20}(?:ভয়|আতঙ্ক)", negatable=False, language="bn"),
    _r(R.IMMEDIATE_DANGER, r"\b(?:ekhon(?:i| e)?|ajke rate)\b.{0,30}\b(?:mere felbe|marche|mar(?:t|d)?(?:e|ch)|churi|knife)\b", negatable=False, language="banglish"),
    # ---------------------------------------------------------------- self-harm
    _r(R.SELF_HARM, r"\b(?:kill(?:ing)? myself|end(?:ing)? my (?:own )?life|take my (?:own )?life|commit suicide|suicidal)\b", negatable=False),
    _r(R.SELF_HARM, r"\b(?:i )?(?:want|wanna|going) to die\b|\bno (?:reason|point) (?:to|in) (?:live|living)\b|\bbetter off (?:dead|without me)\b", negatable=False),
    _r(R.SELF_HARM, r"\b(?:hurt|harm|cut(?:ting)?) myself\b|\bself[- ]harm", negatable=True),
    _r(R.SELF_HARM, r"আত্মহত্যা|নিজেকে শেষ করে|মরে যেতে (?:ইচ্ছা|ইচ্ছে)|বাঁচতে (?:ইচ্ছা|ইচ্ছে) করে না|আর বাঁচতে চাই না|নিজের ক্ষতি করব", negatable=False, language="bn"),
    _r(R.SELF_HARM, r"\b(?:atmohot+a|attohotta|nijeke shesh kor|more jete (?:ichha|icche|iccha)|r? ?bachte (?:chai|ichha|icche) ?na|morte (?:chai|ichha|icche))\b", negatable=False, language="banglish"),
    # ---------------------------------------------------------------- physical violence
    _r(R.PHYSICAL_VIOLENCE, PARTNER + r"\b.{0,30}\b(?:hit|hits|hitting|slapped|slaps|punched|punches|kicked|kicks|beat|beats|beating|choked|chokes|strangled|pushed me|shoved me|threw (?:something|things|a \w+) at me)\b"),
    _r(R.PHYSICAL_VIOLENCE, r"\b(?:hit|slapped|punched|kicked|beat|choked|strangled|shoved|pushed) me\b"),
    _r(R.PHYSICAL_VIOLENCE, r"\b(?:physically (?:abusive|abuses|hurt)|domestic violence)\b"),
    _r(R.PHYSICAL_VIOLENCE, r"(?:গায়ে হাত (?:তোলে|তুলেছে|তুলল)|মারধর|থাপ্পড় (?:মারে|মেরেছে|দিয়েছে)|আমাকে মারে|আমাকে মেরেছে|গলা চেপে|লাথি (?:মারে|মেরেছে))", language="bn"),
    _r(R.PHYSICAL_VIOLENCE, r"\b(?:gaye hat tol(?:e|se|che|eche)|maar ?dhor|mardhor|thappor (?:mare|marse|maree|dise|diyeche)|amake mar(?:e|se|lo|che|eche)|lathi mar(?:e|se|lo))\b", language="banglish"),
    # ---------------------------------------------------------------- sexual coercion
    _r(R.SEXUAL_COERCION, r"\b(?:forc(?:es|ed|ing) me (?:to have sex|into sex|to sleep with)|raped? me|sexual(?:ly)? (?:assault|abuse)|marital rape)\b", negatable=False),
    _r(R.SEXUAL_COERCION, r"\b(?:won't|doesn't|does not|will not) (?:take|accept) no\b.{0,30}\b(?:sex|intimate|bed)\b|\bpressur(?:es|ed|ing) me (?:into|to have) sex\b", negatable=False),
    _r(R.SEXUAL_COERCION, r"জোর করে (?:শারীরিক সম্পর্ক|সেক্স|মেলামেশা)|ধর্ষণ|যৌন নির্যাতন", negatable=False, language="bn"),
    _r(R.SEXUAL_COERCION, r"\bjor kore (?:sex|shar[iy]rik|shomporko|somporko)|dhorshon\b", negatable=False, language="banglish"),
    # ---------------------------------------------------------------- threats
    _r(R.THREATS, r"\bthreat(?:en|ens|ened|ening)\b.{0,40}\b(?:kill|hurt|harm|beat|take (?:the|my) (?:kids|children|baby)|leak|post (?:my |the )?(?:\w+ )?(?:photos|pictures|videos|pics)|ruin|acid)\b"),
    _r(R.THREATS, PARTNER + r"\b.{0,20}\b(?:said|says|told me) (?:he|she|they)(?:'ll| will| would)\b.{0,20}\b(?:kill|hurt|harm) (?:me|my|himself|herself)\b"),
    _r(R.THREATS, r"(?:মেরে ফেলার|ক্ষতি করার|ছবি ছড়িয়ে দেওয়ার|এসিড).{0,10}হুমকি|হুমকি (?:দেয়|দিয়েছে|দিচ্ছে)", language="bn"),
    _r(R.THREATS, r"\bhumki (?:dey|dise|diyeche|dicche|dey je)\b|\b(?:mere felar|chobi chorie deyar|pic leak) humki\b", language="banglish"),
    # ---------------------------------------------------------------- stalking
    _r(R.STALKING, r"\b(?:stalk(?:s|ing|ed)? me|keeps? (?:following|showing up)|follows me (?:everywhere|to work|home)|tracking my (?:location|phone)|put a tracker)\b"),
    _r(R.STALKING, r"\bex\b.{0,40}\b(?:won't stop|keeps?) (?:messaging|calling|texting|contacting|following)\b"),
    _r(R.STALKING, r"পিছু নেয়|অনুসরণ করে|আমার লোকেশন ট্র্যাক|বারবার (?:বাসার|অফিসের) সামনে", language="bn"),
    _r(R.STALKING, r"\b(?:piche piche ashe|follow kore (?:sob|shob) jaygay|location track kore|basar shamne (?:ese|eshe) dariye thake)\b", language="banglish"),
    # ---------------------------------------------------------------- coercive control
    _r(R.COERCIVE_CONTROL, r"\b(?:won't|doesn't|does not|will not|never) let me (?:see|meet|go|talk to|work|leave|have)\b", negatable=False),
    _r(R.COERCIVE_CONTROL, r"\b(?:controls? (?:all )?(?:my|our) money|takes? (?:all )?my (?:salary|money|phone)|isolat(?:es|ed|ing) me|not allowed to (?:go out|see|work|talk))\b"),
    _r(R.COERCIVE_CONTROL, PARTNER + r"\b.{0,20}\b(?:checks? my phone|demands? my passwords?|reads? (?:all )?my messages|monitors? (?:me|my))\b"),
    _r(R.COERCIVE_CONTROL, r"\b(?:i(?:'m| am) )?(?:scared|afraid) of (?:him|her|them|my (?:partner|husband|wife))\b"),
    _r(R.COERCIVE_CONTROL, r"(?:বাইরে যেতে|বন্ধুদের সাথে দেখা করতে|চাকরি করতে|বাপের বাড়ি যেতে) দেয় না|টাকা(?:-পয়সা)? (?:নিয়ন্ত্রণ করে|কেড়ে নেয়|নিয়ে নেয়)|আমার ফোন (?:চেক করে|কেড়ে নেয়)|পাসওয়ার্ড চায়|ওকে ভয় পাই|তাকে ভয় পাই", language="bn"),
    _r(R.COERCIVE_CONTROL, r"\b(?:baire jete dey ?na|bondhuder sathe dekha korte dey ?na|chakri korte dey ?na|baper bari jete dey ?na|taka (?:niye ney|kere ney)|phone check kore|password chay|take bhoy pai|oke bhoy pai)\b", language="banglish"),
    # ---------------------------------------------------------------- repeated humiliation
    _r(R.REPEATED_HUMILIATION, r"\b(?:always|constantly|keeps?|every day)\b.{0,25}\b(?:insult(?:s|ing)?|humiliat(?:es|ing)|belittl(?:es|ing)|calls? me (?:stupid|worthless|ugly|useless|fat))\b"),
    _r(R.REPEATED_HUMILIATION, r"\b(?:humiliates? me|puts? me down) (?:in front of|in public)\b|\bcalls? me (?:worthless|useless|stupid|a burden)\b"),
    _r(R.REPEATED_HUMILIATION, r"(?:সবসময়|সারাক্ষণ|প্রতিদিন|সবার সামনে).{0,25}(?:অপমান করে|ছোট করে|গালি দেয়|অপদার্থ বলে)", language="bn"),
    _r(R.REPEATED_HUMILIATION, r"\b(?:sob ?somoy|shob ?shomoy|protidin|sobar samne|shobar shamne)\b.{0,25}\b(?:opoman kore|choto kore|gali dey|guli dey|opodartho bole)\b", language="banglish"),
    # ---------------------------------------------------------------- surveillance requests (user intent)
    _r(R.SURVEILLANCE_REQUEST, r"\b(?:how (?:can|do|could|to)|help me|ways? to|want to|app to)\b.{0,40}\b(?:spy on|track|hack|read|monitor|see|access|check|secretly (?:check|read))\b.{0,30}\b(?:his|her|their|my (?:partner|husband|wife|boyfriend|girlfriend|bf|gf)(?:'s)?)\b.{0,25}\b(?:phone|messages|whatsapp|messenger|texts|location|chats|email|account|instagram|facebook)\b", negatable=False),
    _r(R.SURVEILLANCE_REQUEST, r"\b(?:install|put) (?:a |an )?(?:spy|spyware|tracking|stalkerware|keylogger)\b|\bspy (?:app|software)\b", negatable=False),
    _r(R.SURVEILLANCE_REQUEST, r"(?:কীভাবে|কিভাবে).{0,30}(?:লুকিয়ে|গোপনে).{0,20}(?:ফোন|মেসেজ|লোকেশন|হোয়াটসঅ্যাপ)|(?:ফোন|মেসেজ|হোয়াটসঅ্যাপ) হ্যাক", negatable=False, language="bn"),
    _r(R.SURVEILLANCE_REQUEST, r"\b(?:kivabe|kibhabe|kemne)\b.{0,40}\b(?:lukiye|gopone|hack|track)\b.{0,30}\b(?:phone|message|msg|whatsapp|location|messenger)\b|\b(?:phone|whatsapp|messenger|fb) hack kor(?:bo|te|ar)\b", negatable=False, language="banglish"),
    # ---------------------------------------------------------------- manipulation / threat requests (user intent)
    _r(R.MANIPULATION_REQUEST, r"\b(?:how (?:can|do|could) i|help me|ways? to|want to|best way to)\b.{0,30}\b(?:manipulate|guilt[- ]trip|gaslight|blackmail|threaten|scare|punish|get revenge on|take revenge on|control)\b", negatable=False),
    _r(R.MANIPULATION_REQUEST, r"\b(?:leak|post|share|send)\b.{0,20}\b(?:her|his|their)\b.{0,15}\b(?:nudes|private (?:photos|pictures|videos)|intimate (?:photos|pictures|videos))\b", negatable=False),
    _r(R.MANIPULATION_REQUEST, r"(?:কীভাবে|কিভাবে).{0,30}(?:ব্ল্যাকমেইল|প্রতিশোধ নেব|ভয় দেখাব|শাস্তি দেব)|(?:ছবি|ভিডিও) ছড়িয়ে দেব", negatable=False, language="bn"),
    _r(R.MANIPULATION_REQUEST, r"\b(?:kivabe|kibhabe|kemne)\b.{0,30}\b(?:blackmail|protishodh|protisodh|bhoy dekhabo|shasti debo|manipulate)\b|\b(?:chobi|pic|video) (?:leak|chorie) (?:korbo|dibo|debo)\b", negatable=False, language="banglish"),
)

NEGATION_BEFORE = re.compile(
    r"\b(?:never|not|n't|no longer|didn't|doesn't|hasn't|has never|wouldn't|won't ever)\b[^.!?\n]{0,20}$", re.IGNORECASE
)
NEGATION_INSIDE = re.compile(r"\b(?:never|not|didn't|doesn't|hasn't|wouldn't)\b", re.IGNORECASE)
NEGATION_AFTER = re.compile(r"^\s*(?:না|নি|নাই|নেই|na\b|ni\b|nai\b|nei\b)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class RuleMatch:
    category: RiskCategory
    weight: float
    language: str
    negated: bool


def match_rules(text: str) -> list[RuleMatch]:
    lowered = text.lower()
    matches: list[RuleMatch] = []
    for rule in RULES:
        for m in rule.pattern.finditer(lowered):
            negated = False
            if rule.negatable:
                before = lowered[max(0, m.start() - 40) : m.start()]
                after = lowered[m.end() : m.end() + 6]
                # Patterns such as "<partner> ... hit" can contain the negation inside the
                # matched span ("he has never hit me"), so check the span too.
                negated = bool(
                    NEGATION_BEFORE.search(before)
                    or NEGATION_INSIDE.search(m.group(0))
                    or NEGATION_AFTER.search(after)
                )
            matches.append(RuleMatch(rule.category, rule.weight, rule.language, negated))
    return matches
