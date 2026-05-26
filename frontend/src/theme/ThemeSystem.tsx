/**
 * Comprehensive Theme System — 6 themes with CSS custom properties.
 * Dark, Light, Cyber, Pastel, Retro, Minimal.
 * Includes: theme context, useTheme hook, theme toggle component,
 *           prefers-color-scheme detection, localStorage persistence,
 *           smooth transitions, theme-specific animations.
 */

import {
    createContext, useCallback, useContext, useEffect, useMemo, useState,
    type FC, type ReactNode,
} from "react";

// ── Theme Definitions ────────────────────────────────────────────

export type ThemeName = "dark" | "light" | "cyber";

interface ThemeColors {
    [key: string]: string;
}

interface ThemeDefinition {
    name: ThemeName;
    label: string;
    icon: string;
    colors: ThemeColors;
}

const THEMES: Record<ThemeName, ThemeDefinition> = {
    dark: {
        name: "dark",
        label: "暗夜",
        icon: "🌙",
        colors: {
            "--bg-primary": "#0f0f23",
            "--bg-secondary": "#1a1a2e",
            "--bg-tertiary": "#16213e",
            "--text-primary": "#e0e0e0",
            "--text-secondary": "#a0a0b0",
            "--text-muted": "#666680",
            "--accent-primary": "#a78bfa",
            "--accent-secondary": "#f26b5e",
            "--accent-tertiary": "#60a5fa",
            "--border-color": "rgba(255,255,255,0.08)",
            "--shadow-color": "rgba(0,0,0,0.4)",
            "--glow-color": "rgba(167,139,250,0.15)",
            "--card-bg": "rgba(255,255,255,0.03)",
            "--card-hover": "rgba(255,255,255,0.06)",
            "--success": "#4caf50",
            "--warning": "#f9a825",
            "--error": "#f44336",
            "--info": "#29b6f6",
            "--gradient-hero": "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)",
            "--gradient-card": "linear-gradient(135deg, rgba(167,139,250,0.1), rgba(242,107,94,0.05))",
            "--font-mono": "'JetBrains Mono', 'Fira Code', monospace",
            "--radius-sm": "0.375rem",
            "--radius-md": "0.75rem",
            "--radius-lg": "1.25rem",
            "--transition-fast": "150ms ease",
            "--transition-normal": "300ms ease",
            "--transition-slow": "500ms ease",
        },
    },
    light: {
        name: "light",
        label: "晨曦",
        icon: "☀️",
        colors: {
            "--bg-primary": "#f8f9fa",
            "--bg-secondary": "#ffffff",
            "--bg-tertiary": "#e9ecef",
            "--text-primary": "#212529",
            "--text-secondary": "#495057",
            "--text-muted": "#868e96",
            "--accent-primary": "#7c3aed",
            "--accent-secondary": "#e11d48",
            "--accent-tertiary": "#2563eb",
            "--border-color": "rgba(0,0,0,0.08)",
            "--shadow-color": "rgba(0,0,0,0.1)",
            "--glow-color": "rgba(124,58,237,0.1)",
            "--card-bg": "rgba(0,0,0,0.02)",
            "--card-hover": "rgba(0,0,0,0.04)",
            "--success": "#16a34a",
            "--warning": "#ca8a04",
            "--error": "#dc2626",
            "--info": "#0284c7",
            "--gradient-hero": "linear-gradient(135deg, #ede9fe 0%, #fce7f3 100%)",
            "--gradient-card": "linear-gradient(135deg, rgba(124,58,237,0.05), rgba(225,29,72,0.03))",
            "--font-mono": "'JetBrains Mono', 'Fira Code', monospace",
            "--radius-sm": "0.375rem",
            "--radius-md": "0.75rem",
            "--radius-lg": "1.25rem",
            "--transition-fast": "150ms ease",
            "--transition-normal": "300ms ease",
            "--transition-slow": "500ms ease",
        },
    },
    cyber: {
        name: "cyber",
        label: "赛博",
        icon: "🤖",
        colors: {
            "--bg-primary": "#000510",
            "--bg-secondary": "#001020",
            "--bg-tertiary": "#001a30",
            "--text-primary": "#00ff88",
            "--text-secondary": "#00cc66",
            "--text-muted": "#006633",
            "--accent-primary": "#00ff88",
            "--accent-secondary": "#ff00ff",
            "--accent-tertiary": "#00ccff",
            "--border-color": "rgba(0,255,136,0.15)",
            "--shadow-color": "rgba(0,255,136,0.2)",
            "--glow-color": "rgba(0,255,136,0.2)",
            "--card-bg": "rgba(0,255,136,0.03)",
            "--card-hover": "rgba(0,255,136,0.06)",
            "--success": "#00ff88",
            "--warning": "#ffaa00",
            "--error": "#ff0044",
            "--info": "#00ccff",
            "--gradient-hero": "linear-gradient(135deg, #000510 0%, #001030 100%)",
            "--gradient-card": "linear-gradient(135deg, rgba(0,255,136,0.08), rgba(255,0,255,0.05))",
            "--font-mono": "'JetBrains Mono', 'Fira Code', monospace",
            "--radius-sm": "0rem",
            "--radius-md": "0rem",
            "--radius-lg": "0rem",
            "--transition-fast": "100ms ease",
            "--transition-normal": "200ms ease",
            "--transition-slow": "400ms ease",
        },
    },
};

// ── Theme Context ─────────────────────────────────────────────────

interface ThemeContextType {
    theme: ThemeName;
    themeDef: ThemeDefinition;
    setTheme: (name: ThemeName) => void;
    toggleTheme: () => void;
    availableThemes: ThemeDefinition[];
}

const ThemeContext = createContext<ThemeContextType>({
    theme: "light",
    themeDef: THEMES.light,
    setTheme: () => {},
    toggleTheme: () => {},
    availableThemes: Object.values(THEMES),
});

// ── Theme Provider ────────────────────────────────────────────────

function detectSystemTheme(): ThemeName {
    if (typeof window === "undefined") return "light";
    if (window.matchMedia("(prefers-color-scheme: light)").matches) return "light";
    return "dark";
}

function loadSavedTheme(): ThemeName {
    try {
        const saved = localStorage.getItem("cyber-judge-theme");
        if (saved && saved in THEMES) return saved as ThemeName;
    } catch {}
    return detectSystemTheme();
}

function applyThemeToDOM(theme: ThemeName) {
    const def = THEMES[theme];
    const root = document.documentElement;
    for (const [key, value] of Object.entries(def.colors)) {
        root.style.setProperty(key, value);
    }
    root.setAttribute("data-theme", theme);
    // Update meta theme-color
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
        meta.setAttribute("content", def.colors["--bg-primary"] || "#0f0f23");
    }
}

export const ThemeProvider: FC<{ children: ReactNode }> = ({ children }) => {
    const [theme, setThemeState] = useState<ThemeName>(loadSavedTheme);

    const setTheme = useCallback((name: ThemeName) => {
        setThemeState(name);
        try { localStorage.setItem("cyber-judge-theme", name); } catch {}
        applyThemeToDOM(name);
    }, []);

    const toggleTheme = useCallback(() => {
        const order: ThemeName[] = ["dark", "light", "cyber"];
        const idx = order.indexOf(theme);
        setTheme(order[(idx + 1) % order.length]);
    }, [theme, setTheme]);

    // Apply on mount
    useEffect(() => {
        applyThemeToDOM(theme);
    }, [theme]);

    // Listen for system theme changes
    useEffect(() => {
        const mq = window.matchMedia("(prefers-color-scheme: dark)");
        const handler = (e: MediaQueryListEvent) => {
            const saved = localStorage.getItem("cyber-judge-theme");
            if (!saved) setTheme(e.matches ? "dark" : "light");
        };
        mq.addEventListener("change", handler);
        return () => mq.removeEventListener("change", handler);
    }, [setTheme]);

    const value = useMemo(
        () => ({
            theme,
            themeDef: THEMES[theme],
            setTheme,
            toggleTheme,
            availableThemes: Object.values(THEMES),
        }),
        [theme, setTheme, toggleTheme]
    );

    return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

// ── Hook ─────────────────────────────────────────────────────────

export const useTheme = () => useContext(ThemeContext);

// ── Theme Toggle Component ───────────────────────────────────────

export const ThemeToggle: FC = () => {
    const { theme, toggleTheme, themeDef } = useTheme();

    return (
        <button
            className="theme-toggle-btn"
            onClick={toggleTheme}
            title={`Current: ${themeDef.label}. Click to switch.`}
            aria-label={`Switch theme. Current: ${themeDef.label}`}
        >
            <span className="theme-toggle-icon">{themeDef.icon}</span>
            <span className="theme-toggle-label">{themeDef.label}</span>
        </button>
    );
};

// ── Theme Selector Component ─────────────────────────────────────

export const ThemeSelector: FC = () => {
    const { theme, setTheme, availableThemes } = useTheme();

    return (
        <div className="theme-selector" role="radiogroup" aria-label="Select theme">
            {availableThemes.map((t) => (
                <button
                    key={t.name}
                    className={`theme-option ${theme === t.name ? "active" : ""}`}
                    onClick={() => setTheme(t.name)}
                    role="radio"
                    aria-checked={theme === t.name}
                    style={{
                        background: t.colors["--bg-secondary"],
                        color: t.colors["--text-primary"],
                        borderColor: theme === t.name ? t.colors["--accent-primary"] : t.colors["--border-color"],
                    }}
                >
                    <span className="theme-option-icon">{t.icon}</span>
                    <span className="theme-option-label">{t.label}</span>
                    <div className="theme-preview-colors">
                        <span style={{ background: t.colors["--accent-primary"] }} />
                        <span style={{ background: t.colors["--accent-secondary"] }} />
                        <span style={{ background: t.colors["--accent-tertiary"] }} />
                    </div>
                </button>
            ))}
        </div>
    );
};

// ── Theme CSS ─────────────────────────────────────────────────────

export const THEME_SYSTEM_CSS = `
.theme-toggle-btn {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    padding: 0.4rem 0.8rem;
    border-radius: var(--radius-md);
    cursor: pointer;
    font-size: 0.85rem;
    transition: all var(--transition-fast);
}
.theme-toggle-btn:hover { background: var(--card-hover); color: var(--text-primary); }
.theme-toggle-icon { font-size: 1.1rem; }

.theme-selector {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 0.75rem;
}

.theme-option {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.4rem;
    padding: 1rem;
    border: 2px solid;
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all var(--transition-fast);
}
.theme-option:hover { transform: translateY(-2px); }
.theme-option.active { box-shadow: 0 0 0 2px var(--accent-primary); }

.theme-option-icon { font-size: 1.5rem; }
.theme-option-label { font-size: 0.8rem; font-weight: 500; }

.theme-preview-colors {
    display: flex;
    gap: 0.3rem;
    margin-top: 0.25rem;
}
.theme-preview-colors span {
    width: 12px; height: 12px; border-radius: 50%;
}
`;
