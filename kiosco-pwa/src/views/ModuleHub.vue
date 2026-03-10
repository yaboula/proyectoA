<script setup>
/**
 * ModuleHub -- Module selector dashboard.
 *
 * Refactored: KioskLayout, removed PrimeVue Card/Button/Tag dependency.
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useOperarioStore } from '../stores/operario'
import KioskLayout from '../components/KioskLayout.vue'
import {
  Factory,
  FlaskConical,
  ArrowRight,
  ShieldCheck,
  LogOut,
  Sparkles,
  Orbit,
} from 'lucide-vue-next'

const router = useRouter()
const store = useOperarioStore()

const allModules = [
  {
    code: 'production',
    title: 'Production pilotee',
    subtitle: 'Flux operateur, poka-yoke et cloture de lot',
    icon: Factory,
    badge: 'Fabrication',
    route: { name: 'tareas' },
    cta: 'Entrer en production',
  },
  {
    code: 'quality',
    title: 'Laboratoire qualite',
    subtitle: 'Liberation des lots, verdict et journal d\'inspection',
    icon: FlaskConical,
    badge: 'Controle Qualite',
    route: { name: 'laboratoire' },
    cta: 'Ouvrir le laboratoire',
  },
]

const modules = computed(() => allModules.filter(m => store.hasModule(m.code)))
const moduleCountLabel = computed(() => `${modules.value.length} zone${modules.value.length > 1 ? 's' : ''}`)

function openModule(route) { router.push(route) }

function logout() {
  store.logout().finally(() => { router.push({ name: 'login' }) })
}
</script>

<template>
  <KioskLayout>
    <div class="glass-panel kiosk-panel rounded-md p-6 md:p-7">
      <div class="gcma-toolbar">
        <div class="max-w-3xl space-y-4">
          <div class="kiosk-chip inline-flex items-center gap-2 rounded-md px-3 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-zinc-400">
            <Sparkles :size="14" />
            Console metier
          </div>
          <div>
            <div class="gcma-section-label">Orientation poste</div>
            <h1 class="mt-2 text-4xl font-black tracking-tight text-zinc-50 md:text-5xl">Hub operateur GCMA</h1>
            <p class="mt-3 max-w-3xl text-base leading-7 text-zinc-400">
              Selection des modules autorises par profil avec acces direct aux flux atelier et laboratoire.
              L'interface privilegie la lisibilite, la densite d'information et la rapidite d'execution.
            </p>
          </div>
        </div>

        <div class="kiosk-panel-soft w-full max-w-md rounded-md p-4">
          <div class="flex items-center gap-3">
            <div class="kiosk-icon-shell flex h-12 w-12 items-center justify-center rounded-md text-zinc-50">
              <ShieldCheck :size="24" />
            </div>
            <div>
              <div class="gcma-section-label">Session active</div>
              <div class="text-lg font-bold text-zinc-50">{{ store.fullName }}</div>
            </div>
          </div>

          <div class="mt-4 grid gap-3 md:grid-cols-2 text-sm text-zinc-400">
            <div class="gcma-stat">
              <div class="gcma-section-label">Entreprise</div>
              <div class="mt-1 font-semibold text-zinc-50">{{ store.operario?.company_abbr }}</div>
            </div>
            <div class="gcma-stat">
              <div class="gcma-section-label">Modules</div>
              <div class="mt-1 font-semibold text-zinc-50">{{ moduleCountLabel }}</div>
            </div>
            <div class="gcma-stat md:col-span-2">
              <div class="gcma-section-label">Profil kiosque</div>
              <div class="mt-1 font-semibold text-zinc-50">{{ store.profileLabel }}</div>
            </div>
          </div>

          <button @click="logout"
                  class="mt-4 h-12 w-full rounded-md border border-zinc-800 bg-zinc-950 px-4 text-zinc-50 text-sm font-semibold flex items-center justify-center gap-2 active:bg-zinc-900 transition">
            <LogOut :size="18" />
            Fermer la session
          </button>
        </div>
      </div>
    </div>

    <div class="grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
      <div class="grid gap-4 lg:grid-cols-2">
        <article v-for="mod in modules" :key="mod.code"
                 class="module-card kiosk-panel overflow-hidden rounded-md">
          <div class="gcma-data-row h-full border border-zinc-800 p-5 md:p-6">
            <div class="flex h-full flex-col gap-5">
              <div class="flex items-start justify-between gap-4">
                <div class="space-y-3">
                  <span class="kiosk-chip inline-block rounded-md px-3 py-2 text-[11px] font-semibold tracking-[0.22em] text-zinc-300">
                    {{ mod.badge }}
                  </span>
                  <div>
                    <h2 class="text-3xl font-black tracking-tight text-zinc-50">{{ mod.title }}</h2>
                    <p class="mt-2 max-w-sm text-sm leading-6 text-zinc-400">{{ mod.subtitle }}</p>
                  </div>
                </div>
                <div class="kiosk-icon-shell flex h-14 w-14 items-center justify-center rounded-md text-zinc-50 bg-zinc-950">
                  <component :is="mod.icon" :size="30" />
                </div>
              </div>

              <div class="grid grid-cols-2 gap-3 text-sm text-zinc-400">
                <div class="gcma-stat">
                  <div class="text-zinc-500">Mode</div>
                  <div class="mt-1 font-semibold text-zinc-50">Tablette terrain</div>
                </div>
                <div class="gcma-stat">
                  <div class="text-zinc-500">Experience</div>
                  <div class="mt-1 font-semibold text-zinc-50">Fat-finger ready</div>
                </div>
              </div>

              <div class="gcma-data-row grid grid-cols-2 gap-3 p-3 text-sm text-zinc-400">
                <div>
                  <div class="gcma-section-label">Statut</div>
                  <div class="mt-1 font-semibold text-zinc-50">Autorise</div>
                </div>
                <div>
                  <div class="gcma-section-label">Route</div>
                  <div class="mt-1 font-semibold text-zinc-50">{{ mod.route.name }}</div>
                </div>
              </div>

              <button @click="openModule(mod.route)"
                      class="mt-auto h-14 rounded-md bg-zinc-50 text-zinc-900 px-5 text-sm font-black uppercase tracking-[0.18em] flex items-center justify-center gap-2 active:bg-zinc-200 transition">
                {{ mod.cta }}
                <ArrowRight :size="18" />
              </button>
            </div>
          </div>
        </article>
      </div>

      <div class="kiosk-panel overflow-hidden rounded-md p-5 md:p-6">
        <div class="space-y-5">
          <div class="flex items-center gap-3">
            <div class="kiosk-icon-shell flex h-12 w-12 items-center justify-center rounded-md text-zinc-50">
              <Orbit :size="22" />
            </div>
            <div>
              <div class="gcma-section-label">Briefing</div>
              <div class="text-2xl font-black text-zinc-50">Console metier</div>
            </div>
          </div>

          <div class="space-y-3 text-sm leading-6 text-zinc-400">
            <p>
              Chaque badge ouvre uniquement les modules autorises par le profil ERPNext de l'employe.
              La separation operateur et laboratoire n'est plus seulement visuelle.
            </p>
            <p>
              Le hub devient un point d'entree metier: production pour le flux cadence operateur,
              laboratoire pour le verdict qualite et la liberation des lots.
            </p>
          </div>

          <div class="grid gap-3">
            <div class="gcma-data-row border border-zinc-800 p-4">
              <div class="gcma-section-label text-zinc-300">Production</div>
              <div class="mt-1 text-sm text-zinc-300">Validation matiere, scans terrain, cloture native ERPNext.</div>
            </div>
            <div class="gcma-data-row border border-zinc-800 p-4">
              <div class="gcma-section-label text-zinc-300">Qualite</div>
              <div class="mt-1 text-sm text-zinc-300">Vue lots, verdict approuve/rejete, inspection liee aux documents natifs.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </KioskLayout>
</template>
