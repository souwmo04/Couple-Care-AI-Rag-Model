import {
  DoorOpen,
  Fence,
  Handshake,
  HeartHandshake,
  House,
  MessagesSquare,
  ShieldQuestion,
  Waves,
  type LucideIcon,
} from 'lucide-react'

export const TOPIC_IDS = [
  'communication',
  'trust_jealousy',
  'emotional_distance',
  'dating_commitment',
  'marriage_family',
  'boundaries_expectations',
  'conflict_resolution',
  'healthy_separation',
] as const

export type TopicId = (typeof TOPIC_IDS)[number]

export const TOPIC_ICONS: Record<TopicId, LucideIcon> = {
  communication: MessagesSquare,
  trust_jealousy: ShieldQuestion,
  emotional_distance: Waves,
  dating_commitment: HeartHandshake,
  marriage_family: House,
  boundaries_expectations: Fence,
  conflict_resolution: Handshake,
  healthy_separation: DoorOpen,
}

/** Topic accent hues — used sparingly for icon tiles. */
export const TOPIC_TONES: Record<TopicId, string> = {
  communication: 'text-lavender bg-lavender-soft',
  trust_jealousy: 'text-accent bg-accent-soft',
  emotional_distance: 'text-lavender bg-lavender-soft',
  dating_commitment: 'text-accent bg-accent-soft',
  marriage_family: 'text-lavender bg-lavender-soft',
  boundaries_expectations: 'text-accent bg-accent-soft',
  conflict_resolution: 'text-lavender bg-lavender-soft',
  healthy_separation: 'text-accent bg-accent-soft',
}

/** Starter sentences placed in the composer (never sent automatically). */
export const TOPIC_STARTERS: Record<'en' | 'bn' | 'banglish', Record<TopicId, string>> = {
  en: {
    communication: 'I feel like my partner doesn’t really listen when I talk about something important. ',
    trust_jealousy: 'I’ve been feeling jealous and unsure whether I can trust my partner. ',
    emotional_distance: 'We’ve started to feel distant, like we only talk about chores and logistics. ',
    dating_commitment: 'We’ve been dating for a while and I’m not sure we want the same future. ',
    marriage_family: 'There is tension between me and my in-laws and it’s affecting our marriage. ',
    boundaries_expectations: 'I want to set a boundary with my partner but I don’t know how to say it. ',
    conflict_resolution: 'We keep having the same argument and it escalates every time. ',
    healthy_separation: 'I’m thinking about ending the relationship and I’m not sure how to decide. ',
  },
  bn: {
    communication: 'মনে হয় গুরুত্বপূর্ণ কিছু বললে আমার সঙ্গী ঠিকমতো শোনে না। ',
    trust_jealousy: 'আমার খুব হিংসা হচ্ছে, আর বুঝতে পারছি না সঙ্গীকে বিশ্বাস করতে পারি কি না। ',
    emotional_distance: 'আমাদের মধ্যে দূরত্ব তৈরি হয়েছে, এখন শুধু সংসারের কাজের কথাই হয়। ',
    dating_commitment: 'আমরা অনেকদিন ধরে সম্পর্কে আছি, কিন্তু নিশ্চিত নই দুজন একই ভবিষ্যৎ চাই কি না। ',
    marriage_family: 'শ্বশুরবাড়ির সঙ্গে টানাপোড়েন চলছে, আর এর প্রভাব আমাদের বিয়েতে পড়ছে। ',
    boundaries_expectations: 'সঙ্গীর সঙ্গে একটা সীমা ঠিক করতে চাই, কিন্তু কীভাবে বলব বুঝতে পারছি না। ',
    conflict_resolution: 'আমাদের একই ঝগড়া বারবার হয়, আর প্রতিবার আরও বেড়ে যায়। ',
    healthy_separation: 'সম্পর্কটা শেষ করার কথা ভাবছি, কিন্তু কীভাবে সিদ্ধান্ত নেব বুঝতে পারছি না। ',
  },
  banglish: {
    communication: 'Mone hoy important kichu bolle amar partner thikmoto shune na. ',
    trust_jealousy: 'Amar khub hingsha hocche, ar bujhte parchi na partner ke bisshash korte pari kina. ',
    emotional_distance: 'Amader moddhe durotto toiri hoyeche, ekhon shudhu kaajer kotha hoy. ',
    dating_commitment: 'Amra onekdin dhore relationship e achi, kintu sure na duijon eki future chai kina. ',
    marriage_family: 'Shoshurbari r sathe tension cholche, ar eta amader biye te effect korche. ',
    boundaries_expectations: 'Partner er sathe ekta boundary set korte chai, kintu kivabe bolbo bujhchi na. ',
    conflict_resolution: 'Amader ek jhogra bar bar hoy, ar protibar aro bere jay. ',
    healthy_separation: 'Relationship ta shesh korar kotha bhabchi, kintu kivabe decide korbo bujhchi na. ',
  },
}

/** Display name for any index topic, including ones without a chat topic card (e.g. "safety"). */
export function topicTitle(copy: { topics: { items: Record<string, { title: string }> }; nav: { safety: string } }, topic: string): string {
  if (topic === 'safety') return copy.nav.safety
  return copy.topics.items[topic]?.title ?? topic
}
