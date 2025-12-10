import { createTamagui } from 'tamagui'
import { createInterFont } from '@tamagui/font-inter'
import { shorthands } from '@tamagui/shorthands'
import { themes, tokens } from '@tamagui/themes'

const headingFont = createInterFont()
const bodyFont = createInterFont()

const config = createTamagui({
    themes,
    tokens: {
        ...tokens,
        color: {
            ...tokens.color,
            neonGreen: '#CCFF00',
            neonBlue: '#00CCFF',
            neonRed: '#FF3333',
            neonYellow: '#FFFF00',
            glassBg: 'rgba(255,255,255,0.05)',
            glassBorder: 'rgba(255,255,255,0.1)',
        }
    },
    shorthands,
    fonts: {
        heading: headingFont,
        body: bodyFont,
    },
    defaultFont: 'body',
})

export type AppConfig = typeof config

declare module 'tamagui' {
    interface TamaguiCustomConfig extends AppConfig { }
}

export default config
