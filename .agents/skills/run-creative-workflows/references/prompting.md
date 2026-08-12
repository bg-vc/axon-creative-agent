# MiniMax H3 prompt fallback

Use this only when the official MiniMax H3 prompt-writing Skill is unavailable.

Write one integrated prompt in this order:

1. State duration, aspect ratio, medium, location, subject, action, and mood.
2. Lock identity, wardrobe, palette, props, and spatial relationships.
3. Divide the clip into a few timed beats. Describe camera and action together.
4. Describe dialogue, effects, ambience, and music in the same timeline.
5. End with a short avoid list covering likely failures, not generic adjectives.

For reference-to-video, assign one job to each supplied reference and use exact
ordered tags such as `<Picture 1>`, `<Video 1>`, and `<Audio 1>`. A picture may
control identity, a video motion/camera, and audio voice cadence. Do not ask all
references to control everything.

Keep the prompt proportional to the clip. A ten-second video normally needs
three or four beats, not a page of unrelated shots.
