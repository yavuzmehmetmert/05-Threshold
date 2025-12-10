import { createTamagui } from 'tamagui'
import { createInterFont } from '@tamagui/font-inter'
import { shorthands } from '@tamagui/shorthands'
import { themes, tokens } from '@tamagui/themes'

const headingFont = createInterFont()
const bodyFont = createInterFont()

const config = createTamagui({
    themes,
    tokens,
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
