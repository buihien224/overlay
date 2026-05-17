// AGSL RuntimeShader
// Light: darker soft blue background + strong blue / purple veins
// Dark: neon blue / purple fluid
// No dFdx / dFdy

uniform vec2 uResolution;
uniform shader uTex;
uniform shader uTexBitmap;
uniform vec2 uTexWH;

uniform float uAnimTime;
uniform vec4 uBound;
uniform float uTranslateY;

uniform vec3 uPoints[4];
uniform vec4 uColors[4];

uniform float uAlphaMulti;
uniform float uNoiseScale;
uniform float uPointOffset;
uniform float uPointRadiusMulti;
uniform float uSaturateOffset;
uniform float uLightOffset;
uniform float uAlphaOffset;
uniform float uShadowColorMulti;
uniform float uShadowColorOffset;
uniform float uShadowNoiseScale;
uniform float uShadowOffset;

float rand(vec2 n)
{
    return fract(sin(dot(n, vec2(12.9898, 4.1414))) * 43758.5453);
}

float noise(vec2 p)
{
    vec2 ip = floor(p);
    vec2 u = fract(p);

    u = u * u * (3.0 - 2.0 * u);

    float res =
        mix(
            mix(rand(ip), rand(ip + vec2(1.0, 0.0)), u.x),
            mix(rand(ip + vec2(0.0, 1.0)), rand(ip + vec2(1.0, 1.0)), u.x),
            u.y
        );

    return res * res;
}

const mat2 m2 = mat2(0.8, -0.6, 0.6, 0.8);

float fbm(vec2 p)
{
    float f = 0.0;

    f += 0.5000 * noise(p);
    p = m2 * p * 2.02;

    f += 0.2500 * noise(p);
    p = m2 * p * 2.03;

    f += 0.1250 * noise(p);
    p = m2 * p * 2.01;

    f += 0.0625 * noise(p);

    return f / 0.769;
}

float pattern(vec2 p)
{
    vec2 q = vec2(fbm(p));

    vec2 r =
        vec2(
            fbm(
                p
                + 4.0 * q
                + vec2(1.7, 9.2)
            )
        );

    r += uAnimTime * 0.15;

    return fbm(p + 1.760 * r);
}

vec4 main(vec2 fragCoord)
{
    vec2 uv = fragCoord / uResolution.xy;

    uv -= 0.5;
    uv.x *= uResolution.x / uResolution.y;
    uv *= 4.5;

    float displacement = pattern(uv);

    vec4 c0 = uColors[0];

    float brightness =
        dot(
            c0.rgb,
            vec3(0.299, 0.587, 0.114)
        );

    float isDark =
        step(
            brightness,
            0.45
        );

    float fluidMask =
        smoothstep(
            0.04,
            0.62,
            displacement
        );

    float fluidDetail =
        sin(
            displacement * 21.0
            + uv.x * 4.2
            - uv.y * 3.0
            + uAnimTime * 0.52
        ) * 0.5 + 0.5;

    float vein =
        smoothstep(
            0.18,
            0.80,
            fluidDetail
        );

    float thinVein =
        smoothstep(
            0.36,
            0.84,
            fluidDetail
        );

    float flowLine =
        sin(
            uv.y * 9.2
            + displacement * 14.0
            + uAnimTime * 0.58
        ) * 0.5 + 0.5;

    float blueLine =
        smoothstep(
            0.36,
            0.84,
            flowLine
        );

    float purpleLine =
        smoothstep(
            0.22,
            0.78,
            sin(
                uv.x * 6.8
                - uv.y * 3.6
                + displacement * 12.0
                - uAnimTime * 0.46
            ) * 0.5 + 0.5
        );

    // =========================
    // LIGHT MODE - DARKER / LESS WHITE
    // =========================

    vec3 softBg      = vec3(0.820, 0.900, 1.000);
    vec3 bgBlue      = vec3(0.700, 0.840, 1.000);

    vec3 paleBlue    = vec3(0.430, 0.700, 1.000);
    vec3 lightBlue   = vec3(0.000, 0.380, 0.960);
    vec3 skyBlue     = vec3(0.000, 0.220, 0.820);

    vec3 softPurple  = vec3(0.350, 0.160, 0.920);
    vec3 deepPurple  = vec3(0.080, 0.000, 0.430);

    float visibleFluid =
        fluidMask * 1.00
        + vein * fluidMask * 0.68
        + thinVein * fluidMask * 0.66
        + purpleLine * fluidMask * 0.42
        + blueLine * fluidMask * 0.36;

    visibleFluid =
        clamp(
            visibleFluid,
            0.0,
            1.0
        );

    vec3 lightBase =
        mix(
            softBg,
            bgBlue,
            fluidMask * 0.48
        );

    lightBase =
        mix(
            lightBase,
            paleBlue,
            fluidMask * 0.52
        );

    lightBase =
        mix(
            lightBase,
            lightBlue,
            vein * fluidMask * 0.82
        );

    lightBase =
        mix(
            lightBase,
            skyBlue,
            blueLine * fluidMask * 0.62
        );

    lightBase =
        mix(
            lightBase,
            softPurple,
            purpleLine * fluidMask * 0.68
        );

    lightBase =
        mix(
            lightBase,
            deepPurple,
            thinVein * fluidMask * 0.72
        );

    lightBase +=
        paleBlue
        * fluidDetail
        * fluidMask
        * 0.030;

    lightBase +=
        softPurple
        * thinVein
        * fluidMask
        * 0.045;

    lightBase +=
        skyBlue
        * blueLine
        * fluidMask
        * 0.035;

    lightBase =
        mix(
            softBg,
            lightBase,
            smoothstep(
                0.02,
                0.48,
                visibleFluid
            )
        );

    // giảm vùng trắng/sáng quá nhiều trong light mode
    lightBase *= 0.88;

    // =========================
    // DARK MODE
    // =========================

    vec3 darkBg      = vec3(0.010, 0.014, 0.030);
    vec3 darkViolet  = vec3(0.080, 0.020, 0.180);
    vec3 neonBlue    = vec3(0.000, 0.780, 1.000);
    vec3 neonPurple  = vec3(0.560, 0.160, 1.000);

    vec3 darkBase =
        mix(
            darkBg,
            darkViolet,
            displacement
        );

    darkBase +=
        neonBlue
        * displacement
        * 0.30;

    darkBase +=
        neonPurple
        * fluidDetail
        * 0.24;

    darkBase +=
        neonBlue
        * thinVein
        * 0.18;

    vec3 col =
        mix(
            lightBase,
            darkBase,
            isDark
        );

    // =========================
    // GLOW
    // =========================

    vec3 lightGlow =
        mix(
            lightBlue,
            softPurple,
            fluidDetail
        );

    vec3 darkGlow =
        mix(
            neonBlue,
            neonPurple,
            fluidDetail
        );

    vec3 glowColor =
        mix(
            lightGlow,
            darkGlow,
            isDark
        );

    float glowStrength =
        mix(
            0.024,
            0.24,
            isDark
        );

    col +=
        glowColor
        * glowStrength
        * (
            0.14
            + displacement * 0.32
        );

    col +=
        mix(lightBlue, neonPurple, isDark)
        * sin(
            uv.x * 3.0
            + uAnimTime * 0.7
        )
        * (
            0.006
            + 0.045 * isDark
        );

    col +=
        mix(paleBlue, neonBlue, isDark)
        * cos(
            uv.y * 4.0
            - uAnimTime * 0.5
        )
        * (
            0.006
            + 0.035 * isDark
        );

    float centerGlow =
        exp(
            -length(uv)
            * 1.85
        );

    col +=
        mix(
            paleBlue,
            neonPurple,
            isDark
        )
        * centerGlow
        * (
            0.006
            + 0.075 * isDark
        );

    // =========================
    // LIGHT MODE DARK CONTRAST
    // =========================

    if (isDark < 0.5)
    {
        float veinContrast =
            smoothstep(
                0.24,
                0.82,
                fluidDetail
            );

        col =
            mix(
                col,
                lightBlue,
                veinContrast * fluidMask * 0.82
            );

        col =
            mix(
                col,
                skyBlue,
                thinVein * fluidMask * 0.70
            );

        col =
            mix(
                col,
                softPurple,
                purpleLine * fluidMask * 0.74
            );

        col =
            mix(
                col,
                deepPurple,
                thinVein * purpleLine * fluidMask * 0.46
            );

        col =
            mix(
                softBg * 0.88,
                col,
                smoothstep(
                    0.02,
                    0.62,
                    visibleFluid
                )
            );

        col =
            clamp(
                col,
                vec3(0.52, 0.66, 0.86),
                vec3(0.92, 0.96, 1.0)
            );
    }

    // sharpen veins without dFdx / dFdy
    if (isDark < 0.5)
    {
        float edge =
            smoothstep(
                0.42,
                0.88,
                abs(
                    sin(
                        displacement * 34.0
                        + uv.x * 4.4
                        - uv.y * 3.2
                    )
                )
            );

        col +=
            skyBlue
            * edge
            * fluidMask
            * 0.18;

        col +=
            deepPurple
            * thinVein
            * fluidMask
            * 0.18;
    }

    // =========================
    // FINAL
    // =========================

    col =
        mix(
            pow(col, vec3(0.98)),
            col,
            isDark
        );

    float vignette =
        1.0
        - dot(
            uv * 0.18,
            uv * 0.18
        );

    vignette =
        mix(
            1.0,
            vignette,
            isDark
        );

    col *= vignette;

    float luma =
        dot(
            col,
            vec3(0.299, 0.587, 0.114)
        );

    col =
        mix(
            vec3(luma),
            col,
            1.30 + uSaturateOffset
        );

    col += uLightOffset * 0.006;

    col *=
        (
            1.0
            - uShadowOffset * 0.025
        );

    col *= uAlphaMulti;

    col =
        clamp(
            col,
            0.0,
            1.0
        );

    return vec4(col, 1.0);
}