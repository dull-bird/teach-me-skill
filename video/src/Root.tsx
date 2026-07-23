import { Composition } from "remotion";
import { TeachMePromo } from "./TeachMePromo";
import manifestZh from "./data/manifest.json";
import manifestEn from "./data/manifest-en.json";

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="TeachMePromo"
        component={TeachMePromo}
        durationInFrames={manifestZh.totalDurationFrames}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{ locale: "zh" }}
      />
      <Composition
        id="TeachMePromoEnglish"
        component={TeachMePromo}
        durationInFrames={manifestEn.totalDurationFrames}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{ locale: "en" }}
      />
    </>
  );
};
