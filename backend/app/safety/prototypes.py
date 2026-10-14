"""Prototype descriptions for the semantic safety classifier.

Each category lists short, general descriptions of how people express that risk — directly
and indirectly — in English, Bangla and Banglish. They are deliberately NOT copies of evaluation
cases. "benign" prototypes describe ordinary relationship difficulties; a message must be closer
to a risk category than to these by a margin before it is flagged.

Editing these changes safety behaviour: keep backend/tests/test_safety_semantic.py passing and
re-run the safety evaluation on the dev split.
"""

from __future__ import annotations

PROTOTYPES: dict[str, list[str]] = {
    "self_harm": [
        "I don't want to be alive anymore.",
        "Everyone would be happier if I were gone.",
        "I keep thinking about ending it all.",
        "I want to disappear forever and never wake up.",
        "I can't go on living like this.",
        "আমার আর বেঁচে থাকতে ইচ্ছা করে না।",
        "আমি না থাকলে সবাই ভালো থাকবে।",
        "সব শেষ করে দিতে ইচ্ছা করে, আর পারছি না।",
        "চিরতরে হারিয়ে যেতে ইচ্ছা করে।",
        "Ami na thakle sobai bhalo thakbe.",
        "Sob shesh kore dite icche kore, ar parchi na.",
        "Chirotore hariye jete icche kore.",
    ],
    "physical_violence": [
        "My partner hurts me physically when he is angry.",
        "I have bruises from what he did and I hide them.",
        "I cover the marks on my body so no one asks questions.",
        "He grabbed me so hard it left marks.",
        "সে রাগ হলে আমাকে শারীরিকভাবে আঘাত করে।",
        "শরীরের দাগগুলো লুকিয়ে রাখি যাতে কেউ প্রশ্ন না করে।",
        "ওর মারের দাগ কাপড় দিয়ে ঢেকে রাখি।",
        "O rag hole amake sharirik bhabe aghat kore.",
        "Shorirer dag gulo lukiye rakhi jate keu proshno na kore.",
    ],
    "coercive_control": [
        "He decides where I can go and who I can talk to.",
        "I have to report my location to him all the time or he gets furious.",
        "My partner tracks everything I do and I feel like a prisoner.",
        "I need his permission to leave the house or spend money.",
        "সে ঠিক করে দেয় আমি কোথায় যাব আর কার সাথে কথা বলব।",
        "সবসময় আমার অবস্থান জানাতে হয়, না হলে সে ভীষণ রেগে যায়।",
        "বাইরে যেতে বা টাকা খরচ করতে তার অনুমতি লাগে।",
        "O thik kore dey ami kothay jabo ar kar sathe kotha bolbo.",
        "Sob somoy amar location janate hoy, na hole o bhishon rege jay.",
        "Baire jete ba taka khoroch korte tar onumoti lage.",
    ],
    "threats": [
        "He warned me something bad will happen if I tell anyone.",
        "She said I will regret it if I ever leave.",
        "He threatens me to keep me quiet about what happens at home.",
        "সে বলেছে কাউকে বললে আমার খারাপ কিছু হবে।",
        "ছেড়ে গেলে পস্তাতে হবে বলে ভয় দেখায়।",
        "O boleche kauke bolle amar kharap kichu hobe.",
        "Chere gele postate hobe bole bhoy dekhay.",
    ],
    "stalking": [
        "My ex always seems to know where I am even though I never told them.",
        "Someone keeps turning up wherever I go after I ended things.",
        "I think my ex is tracking my phone or following me.",
        "প্রাক্তন সবসময় জানে আমি কোথায় আছি, অথচ আমি কাউকে বলিনি।",
        "ব্রেকআপের পর সে যেখানে যাই সেখানেই হাজির হয়।",
        "Amar ex sob somoy jane ami kothay achi, othocho ami kauke bolini.",
        "Breakup er por o jekhane jai shekhanei hajir hoy.",
    ],
    "sexual_coercion": [
        "He makes me be intimate with him even when I refuse.",
        "I feel I have no choice about sex in my marriage.",
        "আমি না চাইলেও সে আমাকে শারীরিক সম্পর্কে বাধ্য করে।",
        "Ami na chaileo o amake sharirik somporke badhyo kore.",
    ],
    "benign": [
        "We argue about chores and money sometimes.",
        "My partner forgets important dates and I feel hurt.",
        "We had a loud fight but made up the same evening.",
        "I feel distant from my partner lately.",
        "I'm jealous when my partner talks to their ex.",
        "My partner is always on their phone when we talk.",
        "We disagree about where to live after the wedding.",
        "I want to end the relationship but I'm not sure.",
        "My in-laws criticise how I keep the house.",
        "I wish my partner listened to me more.",
        "আমরা মাঝে মাঝে টাকা আর সংসারের কাজ নিয়ে ঝগড়া করি।",
        "ইদানীং সঙ্গীর সাথে দূরত্ব অনুভব করি।",
        "শ্বশুরবাড়ির লোকেরা আমার সংসার চালানো নিয়ে সমালোচনা করে।",
        "সে আমার কথা ঠিকমতো শোনে না।",
        "আমাদের মধ্যে এখন কথাবার্তা অনেক কমে গেছে।",
        "দেখা হলে আমরা কী নিয়ে কথা বলব খুঁজে পাই না।",
        "সঙ্গী ফোনে বেশি সময় কাটায়, আমার খারাপ লাগে।",
        "আমাদের মধ্যে আগের মতো ভালোবাসার প্রকাশ নেই।",
        "সঙ্গীর সোশ্যাল মিডিয়া নিয়ে আমার মনে প্রশ্ন জাগে।",
        "বাচ্চা হওয়ার পর আমরা দুজন দুজনকে সময় দিতে পারি না।",
        "আমি চাই সে আমাকে একটু মানসিক সমর্থন দিক।",
        "মেসেজের উত্তর দেরিতে দিলে সে মন খারাপ করে।",
        "Amra majhe majhe taka ar kaaj niye jhogra kori.",
        "Idanin partner er sathe durotto feel kori.",
        "O amar kotha thikmoto shune na.",
        "Shoshurbari r lokera amar songshar niye kotha shonay.",
    ],
}
