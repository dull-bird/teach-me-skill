import { Composition } from "remotion";
import { TeachMePromo, TOTAL_DURATION } from "./TeachMePromo";

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="TeachMePromo"
        component={TeachMePromo}
        durationInFrames={TOTAL_DURATION}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
