<script setup>
const version = '2.7.13'
</script>

<template>
    <div class="layout-footer">
        <!-- Línea separadora decorativa -->
        <div class="footer-divider" />

        <div class="footer-inner">
            <!-- Sección izquierda: marca e info -->
            <div class="footer-left">
                <span class="footer-copyright">
                    &copy; {{ new Date().getFullYear() }}
                    <span class="footer-brand">BinsurMX</span>&#8482;
                </span>
                <span class="footer-separator">|</span>
                <span class="footer-tagline">Plataforma de gestión financiera y tesorería</span>
                <span class="footer-separator">·</span>
                <span class="footer-powered">
                    Impulsado por la tecnología de&nbsp;
                    <a
                        href="https://cytechn.ddns.net"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="footer-link"
                        aria-label="Visitar CyTechnologies"
                    >CyTechnologies&#174;</a>
                </span>
            </div>

            <!-- Sección derecha: versión del producto -->
            <div class="footer-right">
                <span class="footer-version-badge">
                    <span class="version-dot" />
                    Versión&nbsp;<strong>{{ version }}</strong>
                </span>
            </div>
        </div>
    </div>
</template>

<style scoped>
/* ─── Contenedor principal del footer ─── */
.layout-footer {
    background: var(--surface-card, #1e1e2e);
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    padding: 0;
    user-select: none;
}

/* ─── Línea decorativa con gradiente ─── */
.footer-divider {
    height: 2px;
    background: linear-gradient(
        90deg,
        transparent 0%,
        #1a73e8 20%,
        #0ea5e9 45%,
        #10b981 75%,
        transparent 100%
    );
    opacity: 0.75;
}

/* ─── Layout interior ─── */
.footer-inner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.5rem;
    padding: 0.6rem 1rem;
}

/* ─── Zona izquierda ─── */
.footer-left {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.4rem;
    font-size: 1rem;
    color: var(--text-color-secondary, #94a3b8);
    line-height: 1.5;
}

/* Nombre de la plataforma con gradiente azul → verde */
.footer-brand {
    font-weight: 700;
    letter-spacing: 0.03em;
    background: linear-gradient(90deg, #1a73e8 0%, #0ea5e9 50%, #10b981 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.footer-copyright {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 1rem;
    color: var(--text-color-secondary, #94a3b8);
}

.footer-separator {
    color: var(--text-color-secondary, #94a3b8);
    opacity: 0.4;
    font-size: 1rem;
}

.footer-tagline {
    font-size: 1rem;
    color: var(--text-color-secondary, #94a3b8);
    opacity: 0.8;
}

.footer-powered {
    font-size: 1rem;
    color: var(--text-color-secondary, #94a3b8);
    display: inline-flex;
    align-items: center;
}

/* Enlace CyTechnologies */
.footer-link {
    font-weight: 600;
    font-size: 1rem;
    text-decoration: none;
    background: linear-gradient(90deg, #0ea5e9 0%, #10b981 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    transition: opacity 0.2s ease, filter 0.2s ease;
    cursor: pointer;
}

.footer-link:hover {
    opacity: 0.8;
    filter: brightness(1.2);
    text-decoration: underline;
    text-decoration-color: #10b981;
    text-underline-offset: 3px;
}

.footer-link:focus-visible {
    outline: 2px solid #0ea5e9;
    outline-offset: 2px;
    border-radius: 2px;
}

/* ─── Zona derecha: versión ─── */
.footer-right {
    display: flex;
    align-items: center;
    margin-left: auto;
}

.footer-version-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--text-color-secondary, #94a3b8);
    background: rgba(14, 165, 233, 0.08);
    border: 1px solid rgba(14, 165, 233, 0.2);
    border-radius: 999px;
    padding: 0.25rem 0.8rem;
    letter-spacing: 0.02em;
    white-space: nowrap;
}

.footer-version-badge strong {
    color: #0ea5e9;
    font-weight: 700;
}

/* Indicador de estado (punto verde animado) */
.version-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 6px #10b981;
    animation: pulse-dot 2.5s ease-in-out infinite;
    flex-shrink: 0;
}

@keyframes pulse-dot {
    0%, 100% { opacity: 1; box-shadow: 0 0 6px #10b981; }
    50%       { opacity: 0.5; box-shadow: 0 0 12px #10b981; }
}

/* ─── Responsive mobile ─── */
@media (max-width: 640px) {
    .footer-inner {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.4rem;
        padding: 0.75rem 1rem;
    }

    .footer-right {
        align-self: flex-end;
    }

    .footer-tagline {
        display: none;
    }
}
</style>
