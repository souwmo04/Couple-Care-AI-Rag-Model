import '@fontsource-variable/archivo/wdth.css'
import '@fontsource-variable/noto-sans-bengali'
import '@fontsource-variable/jetbrains-mono'
import { Composition } from 'remotion'
import { Promo } from './Promo'
import timeline from './timeline.json'

export const RemotionRoot = () => (
  <>
    {/* Facebook feed (4:5) — the main version. */}
    <Composition
      id="Promo"
      component={Promo}
      durationInFrames={timeline.durationInFrames}
      fps={timeline.fps}
      width={1080}
      height={1350}
    />
    {/* Reels / Stories (9:16): same stage, extra background above and below. */}
    <Composition
      id="PromoVertical"
      component={Promo}
      durationInFrames={timeline.durationInFrames}
      fps={timeline.fps}
      width={1080}
      height={1920}
    />
  </>
)
