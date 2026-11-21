pills => pills.map(p => {
    const s = p.querySelector('.rating-stars'),
        r = s.getBoundingClientRect(),
        target = p.getBoundingClientRect();
    return {
        w: r.width,
        h: r.height,
        target: target.height,
        text: s.textContent.length,
        slots: s.children.length,
        empty: s.querySelectorAll('.rating-star-empty').length,
        ink: getComputedStyle(s).color,
        bg: getComputedStyle(s).backgroundImage,
        fs: parseFloat(getComputedStyle(s).fontSize),
        proportional: [...s.children].every(c => getComputedStyle(c)
            .transform === 'none'),
        glow: getComputedStyle(s.firstElementChild).textShadow,
        faceShadow: getComputedStyle(s).boxShadow,
        // Measure painted glyph ink, not flex slots. Empty slots use
        // the same glyph via ::before. Overlap between adjacent stars
        // is intended; escaping the link target is not.
        inTarget: [...s.children].every(c => {
            const b = c.getBoundingClientRect(),
                style = getComputedStyle(c);
            const ctx = document.createElement('canvas')
                .getContext('2d');
            ctx.font =
                `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
            const m = ctx.measureText('★');
            const x = b.left + (b.width - m.width) / 2;
            const baseline = b.top + (b.height - (m
                    .fontBoundingBoxAscent + m
                    .fontBoundingBoxDescent)) / 2 + m
                .fontBoundingBoxAscent;
            const ink = {
                left: x - m.actualBoundingBoxLeft,
                right: x + m.actualBoundingBoxRight,
                top: baseline - m.actualBoundingBoxAscent,
                bottom: baseline + m
                    .actualBoundingBoxDescent
            };
            // Check actual clipping ancestors, including page cards,
            // cells and scroll containers, not only the isolated face.
            let ancestor = c;
            while (ancestor && ancestor !== document.body) {
                const cs = getComputedStyle(ancestor),
                    bounds = ancestor.getBoundingClientRect();
                // The scrollport is the padding box, excluding borders
                // and scrollbars. Border ink is not visible content.
                const clip = {
                    left: bounds.left + ancestor
                        .clientLeft,
                    top: bounds.top + ancestor.clientTop
                };
                clip.right = clip.left + ancestor.clientWidth;
                clip.bottom = clip.top + ancestor.clientHeight;
                if (['hidden', 'clip', 'scroll', 'auto']
                    .includes(cs.overflowX) && (ink.left < clip
                        .left - .5 || ink.right > clip.right +
                        .5)) return false;
                if (['hidden', 'clip', 'scroll', 'auto']
                    .includes(cs.overflowY) && (ink.top < clip
                        .top - .5 || ink.bottom > clip.bottom +
                        .5)) return false;
                ancestor = ancestor.parentElement;
            }
            return x - m.actualBoundingBoxLeft >= target.left -
                .5 &&
                x + m.actualBoundingBoxRight <= target.right +
                .5 &&
                baseline - m.actualBoundingBoxAscent >= target
                .top - .5 &&
                baseline + m.actualBoundingBoxDescent <= target
                .bottom + .5;
        })
    };
})
