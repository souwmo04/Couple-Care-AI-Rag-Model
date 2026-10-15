// Long-form copy for /about, /privacy and /safety in English and Bangla.

export interface InfoSection {
  heading: string
  body?: string[]
  list?: string[]
}

export interface InfoPage {
  eyebrow: string
  title: string
  lead: string
  sections: InfoSection[]
}

type PageSet = { about: InfoPage; privacy: InfoPage; safety: InfoPage }

export const INFO: Record<'en' | 'bn', PageSet> = {
  en: {
    about: {
      eyebrow: 'Our approach',
      title: 'A careful companion for thinking things through.',
      lead: 'CoupleCare AI is an open, locally run assistant that helps adults reflect on relationship difficulties — in English, Bangla and Banglish — using retrieval-augmented generation.',
      sections: [
        {
          heading: 'What it does',
          body: [
            'You describe what is happening. The assistant acknowledges how it feels, offers a few plausible ways of seeing the situation, suggests one or two practical next steps, and — where useful — gives an example of words you could use. When the local knowledge base contains relevant material, the reply cites it so you can read the source yourself.',
          ],
        },
        {
          heading: 'What it cannot do',
          list: [
            'It is not therapy, counselling, medical care, legal advice or a crisis service.',
            'It cannot know your partner’s thoughts, feelings or intentions. One message — from one side — is never enough to judge another person’s motives.',
            'It does not diagnose anyone and does not predict how a relationship will turn out.',
            'It does not decide who is right, and it does not assume reconciliation is always the goal. Ending a relationship can be a valid choice.',
          ],
        },
        {
          heading: 'How local inference works',
          body: [
            'Replies are written by a small open-weight language model (for example a 4-billion-parameter model in GGUF format) running through llama.cpp on your own computer. The backend sends your message, recent conversation turns and retrieved passages to that local server at 127.0.0.1. No hosted AI API is used for ordinary chat.',
            'If the model server is not running, the app tells you that AI generation is offline. It never substitutes a pre-written answer and presents it as model output. Pre-written safety messages are clearly labelled as such.',
          ],
        },
        {
          heading: 'How sources are selected',
          body: [
            'Only documents listed in a local source manifest — each with a recorded licence or permission — are indexed. For every question, a multilingual embedding model and a keyword (BM25) index each find candidate passages; the results are merged, filtered by a relevance threshold and de-duplicated. The model is instructed to cite only the passages it was given, and citations that do not match a retrieved passage are removed.',
            'The bundled knowledge base contains synthetic example documents written for development. They are labelled “Synthetic example” wherever they appear and are not authoritative guidance.',
          ],
        },
        {
          heading: 'Why answers may be wrong',
          list: [
            'Small local models make mistakes, can misunderstand context, and may write less naturally in Bangla than in English.',
            'Retrieval can miss relevant passages or surface less relevant ones, especially for Romanized Bangla.',
            'The knowledge base is limited to what has been added to it.',
            'The assistant only hears your side of the story.',
          ],
        },
        {
          heading: 'Seeking qualified support',
          body: [
            'For ongoing difficulties, a qualified couples therapist, family counsellor or psychologist can offer what an app cannot: an informed, accountable relationship over time. If there is violence, fear or control in the relationship, individual support from a specialised domestic-violence service is usually safer than joint counselling.',
          ],
        },
      ],
    },
    privacy: {
      eyebrow: 'Privacy',
      title: 'What stays on your computer — and what does not.',
      lead: 'CoupleCare is designed so that ordinary use does not send your conversations anywhere. Here is exactly what is stored, where, and how to delete it.',
      sections: [
        {
          heading: 'Local processing',
          body: [
            'The interface, the backend (bound to 127.0.0.1), the language model server and the knowledge index all run on your computer. The backend refuses to start if configured to use a non-local model server. There are no analytics or tracking scripts, and fonts are bundled locally.',
            'An internet connection is needed only for the initial download of dependencies and models.',
          ],
        },
        {
          heading: 'What is stored',
          list: [
            'Preferences such as theme, language and text size — in your browser’s local storage (or session storage in guest mode).',
            'A random browser identifier, so that conversations cannot be read from another browser.',
            'Conversation history — only if you turn on “Save conversation history”. It is stored in data/user/conversations.sqlite3 on this computer.',
            'Model and retrieval settings — in data/user/settings.json. These contain no message content.',
          ],
        },
        {
          heading: 'What is not stored',
          list: [
            'By default, conversations are kept only in the backend’s memory and are gone when it stops.',
            'Message text is not written to log files by default.',
            'Your conversations are never added to the knowledge base.',
            'Evaluation traces are not recorded unless an operator explicitly enables them.',
          ],
        },
        {
          heading: 'How to delete your data',
          list: [
            'Delete a single conversation from the chat sidebar.',
            'Delete all conversations from the sidebar or from Settings → Privacy. You will be asked to confirm.',
            'Clear local preferences from Settings → Privacy.',
            'Guest mode saves nothing beyond the current browser tab.',
            'To remove everything, stop the app and delete the data/user folder.',
          ],
        },
        {
          heading: 'Limits of local privacy',
          body: [
            'Running locally reduces what leaves your device, but it does not make your device secure. Malware, a compromised operating system, a shared computer account, or someone with physical access could still read stored conversations or preferences. If someone may be monitoring your device, consider using guest mode, keeping history off, or using a device they cannot access.',
          ],
        },
      ],
    },
    safety: {
      eyebrow: 'Safety',
      title: 'How CoupleCare responds when something is not safe.',
      lead: 'A dedicated safety layer — separate from the language model — checks every message. It is designed to take danger seriously without treating every argument as abuse.',
      sections: [
        {
          heading: 'If you are in immediate danger',
          body: [
            'Contact your local emergency number, or go somewhere with other people around. CoupleCare is a chatbot: it cannot call anyone, does not know where you are, and cannot send help.',
          ],
        },
        {
          heading: 'What the safety layer looks for',
          list: [
            'Immediate danger and threats to life.',
            'Thoughts of suicide or self-harm.',
            'Physical violence, sexual coercion, threats and stalking.',
            'Coercive control (isolation, monitoring, controlling money) and repeated humiliation.',
            'Requests to spy on, track, manipulate, threaten or blackmail a partner.',
          ],
          body: [
            'It combines deterministic patterns in English, Bangla and Banglish with a cue-combination check. These are tested separately in each language. It is not perfect: it can miss things, and it can occasionally misread ordinary situations.',
          ],
        },
        {
          heading: 'How responses change',
          list: [
            'Immediate danger or self-harm: a pre-written, clearly labelled safety message is shown instead of a generated reply.',
            'Violence, coercion, threats or stalking: the reply prioritises your safety, does not suggest confronting your partner or joint counselling, and points to specialised support. In Bangla and Banglish this first reply is a pre-written, clearly labelled message, because the local model did not follow the safety instructions reliably in those languages.',
            'Signs of control or humiliation with unclear context: the assistant takes it seriously and may gently ask whether you feel safe.',
            'Requests to monitor or manipulate someone: the assistant declines and offers to help with the underlying worry instead.',
          ],
        },
        {
          heading: 'Support contacts',
          body: [
            'Phone numbers are never generated by the model. CoupleCare includes a small directory of support services, each checked against an official or reputable source with the date of verification. Contacts appear only after you choose your region in Settings — the app does not guess your country from your language. Generated replies are scanned, and any phone number that is not in the verified directory is removed.',
          ],
        },
        {
          heading: 'Why it will not judge your partner’s motives',
          body: [
            'One message describes one moment from one perspective. People’s behaviour has many possible explanations, and guessing at another person’s intentions can lead to unfair conclusions — or to missing real danger. The assistant therefore describes behaviour and its impact, offers several interpretations, and helps you decide what you need.',
          ],
        },
      ],
    },
  },
  bn: {
    about: {
      eyebrow: 'আমাদের পদ্ধতি',
      title: 'ভেবে দেখার জন্য একজন যত্নশীল সঙ্গী।',
      lead: 'CoupleCare AI একটি ওপেন, লোকালি চলা সহকারী, যা রিট্রিভাল-ভিত্তিক জেনারেশন ব্যবহার করে প্রাপ্তবয়স্কদের সম্পর্কের সমস্যা নিয়ে ভাবতে সাহায্য করে — English, বাংলা ও Banglish-এ।',
      sections: [
        {
          heading: 'এটি কী করে',
          body: [
            'আপনি কী হচ্ছে তা লেখেন। সহকারী আপনার অনুভূতি স্বীকার করে, পরিস্থিতি দেখার কয়েকটি সম্ভাব্য দৃষ্টিভঙ্গি দেয়, এক-দুটি বাস্তব পদক্ষেপের পরামর্শ দেয়, আর দরকার হলে বলার মতো কথার উদাহরণ দেয়। লোকাল জ্ঞানভান্ডারে প্রাসঙ্গিক তথ্য থাকলে উত্তরে তার উল্লেখ থাকে, যাতে আপনি নিজেই উৎসটি পড়তে পারেন।',
          ],
        },
        {
          heading: 'যা এটি পারে না',
          list: [
            'এটি থেরাপি, কাউন্সেলিং, চিকিৎসা, আইনি পরামর্শ বা সংকট-সেবা নয়।',
            'এটি আপনার সঙ্গীর চিন্তা, অনুভূতি বা উদ্দেশ্য জানতে পারে না। একপক্ষের একটি বার্তা কখনোই আরেকজনের উদ্দেশ্য বিচারের জন্য যথেষ্ট নয়।',
            'এটি কারও রোগ নির্ণয় করে না এবং সম্পর্ক কোথায় গিয়ে দাঁড়াবে তা বলে দেয় না।',
            'কে ঠিক তা এটি ঠিক করে না, আর মিটমাটই সবসময় লক্ষ্য — এমনও ধরে নেয় না। সম্পর্ক শেষ করাও একটি বৈধ সিদ্ধান্ত হতে পারে।',
          ],
        },
        {
          heading: 'লোকাল মডেল কীভাবে কাজ করে',
          body: [
            'উত্তর লেখে একটি ছোট ওপেন-ওয়েট ভাষা মডেল (যেমন GGUF ফরম্যাটে ৪০০ কোটি প্যারামিটারের মডেল), যা llama.cpp-এর মাধ্যমে আপনার কম্পিউটারেই চলে। ব্যাকএন্ড আপনার বার্তা, সাম্প্রতিক কথোপকথন আর খুঁজে পাওয়া অংশগুলো 127.0.0.1-এর সেই লোকাল সার্ভারে পাঠায়। সাধারণ চ্যাটে কোনো হোস্টেড AI API ব্যবহার হয় না।',
            'মডেল সার্ভার না চললে অ্যাপ জানিয়ে দেয় যে AI উত্তর তৈরি বন্ধ আছে। এটি কখনো আগে থেকে লেখা উত্তরকে মডেলের উত্তর বলে দেখায় না। আগে থেকে লেখা নিরাপত্তা-বার্তাগুলো স্পষ্টভাবে চিহ্নিত থাকে।',
          ],
        },
        {
          heading: 'সূত্র কীভাবে বাছাই হয়',
          body: [
            'শুধু লোকাল সোর্স ম্যানিফেস্টে তালিকাভুক্ত নথি — প্রতিটির লাইসেন্স বা অনুমতিসহ — ইনডেক্স করা হয়। প্রতিটি প্রশ্নের জন্য একটি বহুভাষিক এমবেডিং মডেল ও একটি শব্দভিত্তিক (BM25) ইনডেক্স আলাদাভাবে অংশ খোঁজে; ফলাফল একত্র করে প্রাসঙ্গিকতার সীমা দিয়ে ছাঁকা হয় এবং পুনরাবৃত্তি বাদ দেওয়া হয়। মডেলকে শুধু দেওয়া অংশগুলোর উল্লেখ করতে বলা হয়, আর খুঁজে পাওয়া অংশের সঙ্গে না মেলা উল্লেখ মুছে ফেলা হয়।',
            'সঙ্গে দেওয়া জ্ঞানভান্ডারে উন্নয়নের জন্য লেখা কৃত্রিম উদাহরণ রয়েছে। যেখানেই দেখা যাক, এগুলো "কৃত্রিম উদাহরণ" হিসেবে চিহ্নিত থাকে এবং প্রামাণ্য পরামর্শ নয়।',
          ],
        },
        {
          heading: 'উত্তর কেন ভুল হতে পারে',
          list: [
            'ছোট লোকাল মডেল ভুল করে, প্রসঙ্গ ভুল বুঝতে পারে, এবং ইংরেজির চেয়ে বাংলায় কম স্বাভাবিকভাবে লিখতে পারে।',
            'অনুসন্ধানে প্রাসঙ্গিক অংশ বাদ পড়তে পারে বা কম প্রাসঙ্গিক অংশ আসতে পারে, বিশেষ করে রোমান হরফের বাংলায়।',
            'জ্ঞানভান্ডারে যা যোগ করা হয়েছে, তার বাইরে কিছু নেই।',
            'সহকারী শুধু আপনার দিকের গল্প শোনে।',
          ],
        },
        {
          heading: 'যোগ্য সহায়তা নেওয়া',
          body: [
            'দীর্ঘদিনের সমস্যার জন্য একজন যোগ্য কাপল থেরাপিস্ট, পারিবারিক কাউন্সেলর বা মনোবিজ্ঞানী এমন কিছু দিতে পারেন যা অ্যাপ পারে না: সময়ের সঙ্গে গড়ে ওঠা, জবাবদিহিমূলক সম্পর্ক। সম্পর্কে সহিংসতা, ভয় বা নিয়ন্ত্রণ থাকলে একসঙ্গে কাউন্সেলিংয়ের চেয়ে বিশেষায়িত পারিবারিক সহিংসতা-সহায়তা সংস্থার কাছ থেকে ব্যক্তিগত সহায়তা সাধারণত বেশি নিরাপদ।',
          ],
        },
      ],
    },
    privacy: {
      eyebrow: 'গোপনীয়তা',
      title: 'কী আপনার কম্পিউটারে থাকে — আর কী থাকে না।',
      lead: 'CoupleCare এমনভাবে তৈরি যে সাধারণ ব্যবহারে আপনার কথোপকথন কোথাও পাঠানো হয় না। ঠিক কী, কোথায় সংরক্ষিত হয় আর কীভাবে মুছবেন, তা এখানে।',
      sections: [
        {
          heading: 'লোকাল প্রক্রিয়াকরণ',
          body: [
            'ইন্টারফেস, ব্যাকএন্ড (127.0.0.1-এ সীমাবদ্ধ), ভাষা মডেল সার্ভার আর জ্ঞানভান্ডারের ইনডেক্স — সবই আপনার কম্পিউটারে চলে। লোকাল নয় এমন মডেল সার্ভার কনফিগার করলে ব্যাকএন্ড চালুই হয় না। কোনো অ্যানালিটিক্স বা ট্র্যাকিং স্ক্রিপ্ট নেই, আর ফন্টগুলোও অ্যাপের সঙ্গেই থাকে।',
            'শুধু প্রথমবার প্রয়োজনীয় সফটওয়্যার ও মডেল ডাউনলোডের জন্য ইন্টারনেট লাগে।',
          ],
        },
        {
          heading: 'কী সংরক্ষিত হয়',
          list: [
            'থিম, ভাষা, লেখার আকারের মতো পছন্দ — ব্রাউজারের লোকাল স্টোরেজে (গেস্ট মোডে সেশন স্টোরেজে)।',
            'একটি এলোমেলো ব্রাউজার শনাক্তকারী, যাতে অন্য ব্রাউজার থেকে কথোপকথন পড়া না যায়।',
            'কথোপকথনের ইতিহাস — শুধু "কথোপকথনের ইতিহাস সংরক্ষণ" চালু করলে, এই কম্পিউটারের data/user/conversations.sqlite3 ফাইলে।',
            'মডেল ও অনুসন্ধান সেটিংস — data/user/settings.json-এ। এতে কোনো বার্তার লেখা থাকে না।',
          ],
        },
        {
          heading: 'কী সংরক্ষিত হয় না',
          list: [
            'ডিফল্টভাবে কথোপকথন শুধু ব্যাকএন্ডের মেমোরিতে থাকে এবং এটি বন্ধ হলে মুছে যায়।',
            'ডিফল্টভাবে বার্তার লেখা লগ ফাইলে লেখা হয় না।',
            'আপনার কথোপকথন কখনো জ্ঞানভান্ডারে যোগ হয় না।',
            'অপারেটর আলাদাভাবে চালু না করলে মূল্যায়নের কোনো ট্রেস রাখা হয় না।',
          ],
        },
        {
          heading: 'কীভাবে আপনার তথ্য মুছবেন',
          list: [
            'চ্যাটের সাইডবার থেকে একটি কথোপকথন মুছুন।',
            'সাইডবার বা সেটিংস → গোপনীয়তা থেকে সব কথোপকথন মুছুন। নিশ্চিত করতে বলা হবে।',
            'সেটিংস → গোপনীয়তা থেকে লোকাল পছন্দ মুছুন।',
            'গেস্ট মোডে বর্তমান ব্রাউজার ট্যাবের বাইরে কিছুই সংরক্ষিত হয় না।',
            'সবকিছু মুছতে অ্যাপ বন্ধ করে data/user ফোল্ডারটি মুছে ফেলুন।',
          ],
        },
        {
          heading: 'লোকাল গোপনীয়তার সীমা',
          body: [
            'লোকালি চালালে ডিভাইসের বাইরে তথ্য যাওয়া কমে, কিন্তু তাতে ডিভাইস নিরাপদ হয়ে যায় না। ম্যালওয়্যার, আক্রান্ত অপারেটিং সিস্টেম, শেয়ার করা কম্পিউটার অ্যাকাউন্ট, বা কম্পিউটারে সরাসরি হাত দিতে পারা কেউ সংরক্ষিত কথোপকথন বা পছন্দ পড়তে পারে। কেউ আপনার ডিভাইসে নজর রাখতে পারে মনে হলে গেস্ট মোড ব্যবহার করুন, ইতিহাস বন্ধ রাখুন, অথবা এমন ডিভাইস ব্যবহার করুন যেটিতে তার প্রবেশাধিকার নেই।',
          ],
        },
      ],
    },
    safety: {
      eyebrow: 'নিরাপত্তা',
      title: 'কিছু নিরাপদ না হলে CoupleCare কীভাবে সাড়া দেয়।',
      lead: 'ভাষা মডেল থেকে আলাদা একটি নিরাপত্তা স্তর প্রতিটি বার্তা যাচাই করে। প্রতিটি ঝগড়াকে নির্যাতন না ধরে বিপদকে গুরুত্ব দেওয়ার জন্যই এটি তৈরি।',
      sections: [
        {
          heading: 'আপনি যদি এখনই বিপদে থাকেন',
          body: [
            'আপনার এলাকার জরুরি নম্বরে যোগাযোগ করুন, অথবা এমন জায়গায় যান যেখানে অন্য মানুষ আছে। CoupleCare একটি চ্যাটবট: এটি কাউকে ফোন করতে পারে না, আপনি কোথায় আছেন জানে না, এবং সাহায্য পাঠাতে পারে না।',
          ],
        },
        {
          heading: 'নিরাপত্তা স্তর কী খোঁজে',
          list: [
            'তাৎক্ষণিক বিপদ ও প্রাণনাশের হুমকি।',
            'আত্মহত্যা বা আত্মক্ষতির চিন্তা।',
            'শারীরিক সহিংসতা, যৌন জবরদস্তি, হুমকি ও পিছু নেওয়া।',
            'নিয়ন্ত্রণমূলক আচরণ (বিচ্ছিন্ন করা, নজরদারি, টাকা নিয়ন্ত্রণ) ও বারবার অপমান।',
            'সঙ্গীর ওপর গোপনে নজর রাখা, ট্র্যাক করা, ম্যানিপুলেট করা, হুমকি বা ব্ল্যাকমেইল করার অনুরোধ।',
          ],
          body: [
            'এটি English, বাংলা ও Banglish-এর নির্দিষ্ট প্যাটার্নের সঙ্গে একাধিক সংকেত মিলিয়ে দেখার পদ্ধতি একত্রে ব্যবহার করে। প্রতিটি ভাষায় আলাদাভাবে পরীক্ষা করা হয়েছে। তবে এটি নিখুঁত নয়: কিছু বাদ পড়তে পারে, আবার কখনো সাধারণ পরিস্থিতিকেও ভুল বুঝতে পারে।',
          ],
        },
        {
          heading: 'উত্তর কীভাবে বদলায়',
          list: [
            'তাৎক্ষণিক বিপদ বা আত্মক্ষতি: তৈরি করা উত্তরের বদলে আগে থেকে লেখা, স্পষ্টভাবে চিহ্নিত নিরাপত্তা-বার্তা দেখানো হয়।',
            'সহিংসতা, জবরদস্তি, হুমকি বা পিছু নেওয়া: উত্তর আপনার নিরাপত্তাকে অগ্রাধিকার দেয়, সঙ্গীর মুখোমুখি হতে বা একসঙ্গে কাউন্সেলিংয়ে যেতে বলে না, এবং বিশেষায়িত সহায়তার কথা জানায়। বাংলা ও বাংলিশে এই প্রথম উত্তরটি আগে থেকে লেখা, স্পষ্টভাবে চিহ্নিত বার্তা, কারণ ওই ভাষাগুলোতে লোকাল মডেল নিরাপত্তা-নির্দেশনা নির্ভরযোগ্যভাবে মানেনি।',
            'অস্পষ্ট প্রসঙ্গে নিয়ন্ত্রণ বা অপমানের লক্ষণ: সহকারী বিষয়টিকে গুরুত্ব দেয় এবং আলতো করে জিজ্ঞেস করতে পারে আপনি নিরাপদ বোধ করছেন কি না।',
            'কারও ওপর নজর রাখা বা ম্যানিপুলেট করার অনুরোধ: সহকারী সাহায্য করতে অস্বীকার করে এবং এর পেছনের দুশ্চিন্তা নিয়ে সাহায্যের প্রস্তাব দেয়।',
          ],
        },
        {
          heading: 'সহায়তার যোগাযোগ',
          body: [
            'ফোন নম্বর কখনো মডেল তৈরি করে না। CoupleCare-এ সহায়তা সেবার একটি ছোট তালিকা আছে, যার প্রতিটি সরকারি বা নির্ভরযোগ্য উৎসের সঙ্গে মিলিয়ে যাচাইয়ের তারিখসহ রাখা। সেটিংসে আপনার অঞ্চল বেছে নেওয়ার পরই এগুলো দেখা যায় — অ্যাপ আপনার ভাষা দেখে দেশ অনুমান করে না। তৈরি করা উত্তর যাচাই করা হয়, আর যাচাই করা তালিকায় নেই এমন যেকোনো ফোন নম্বর মুছে ফেলা হয়।',
          ],
        },
        {
          heading: 'কেন এটি আপনার সঙ্গীর উদ্দেশ্য বিচার করবে না',
          body: [
            'একটি বার্তা একটি মুহূর্তকে একজনের দৃষ্টিকোণ থেকে বর্ণনা করে। মানুষের আচরণের অনেক সম্ভাব্য ব্যাখ্যা থাকে, আর অন্যের উদ্দেশ্য আন্দাজ করলে অন্যায্য সিদ্ধান্তে পৌঁছানো — বা আসল বিপদ চোখ এড়িয়ে যাওয়া — দুটোই ঘটতে পারে। তাই সহকারী আচরণ ও তার প্রভাব বর্ণনা করে, কয়েকটি ব্যাখ্যা দেয়, এবং আপনার কী প্রয়োজন তা ঠিক করতে সাহায্য করে।',
          ],
        },
      ],
    },
  },
}
