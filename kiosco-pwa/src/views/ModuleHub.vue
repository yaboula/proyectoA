<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useOperarioStore } from '../stores/operario'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
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
    title: 'Production pilotée',
    subtitle: 'Flux opérateur, poka-yoke et clôture de lot',
    icon: Factory,
    accent: 'from-emerald-500/22 via-teal-500/10 to-transparent',
    border: 'border-emerald-500/30',
    badge: 'Fabrication',
    route: { name: 'tareas' },
    cta: 'Entrer en production',
    ctaClass: '!bg-gradient-to-r !from-emerald-400 !to-teal-300 !text-slate-950 hover:!from-emerald-300 hover:!to-teal-200',
  },
  {
    code: 'quality',
    title: 'Laboratoire qualité',
    subtitle: 'Libération des lots, verdict et journal d’inspection',
    icon: FlaskConical,
    accent: 'from-orange-500/20 via-amber-500/10 to-transparent',
    border: 'border-orange-500/30',
    badge: 'Contrôle Qualité',
    route: { name: 'laboratoire' },
    cta: 'Ouvrir le laboratoire',
    ctaClass: '!bg-gradient-to-r !from-orange-400 !to-amber-300 !text-slate-950 hover:!from-orange-300 hover:!to-amber-200',
  },
]

const modules = computed(() => allModules.filter((module) => store.hasModule(module.code)))
const moduleCountLabel = computed(() => `${modules.value.length} zone${modules.value.length > 1 ? 's' : ''}`)

function openModule(route) {
  router.push(route)
}

function logout() {
  store.logout().finally(() => {
    router.push({ name: 'login' })
  })
}
</script>

<template>
  <div class="min-h-dvh px-5 py-6 text-slate-100">
    <section class="mx-auto flex min-h-[calc(100dvh-3rem)] max-w-7xl flex-col gap-6">
      <div class="glass-panel kiosk-panel relative overflow-hidden rounded-[28px] p-6 md:p-8">
        <div class="absolute inset-y-0 right-0 w-1/2 bg-[radial-gradient(circle_at_center,_rgba(245,158,11,0.14),_transparent_55%)]" />
        <div class="relative z-10 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div class="max-w-3xl space-y-4">
            <div class="kiosk-chip inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.28em] text-slate-300">
              <Sparkles :size="14" />
              Control Room
            </div>
            <div class="space-y-2">
              <h1 class="text-4xl font-black tracking-tight text-white md:text-6xl">
                Poste opérateur
                <span class="bg-gradient-to-r from-teal-300 via-emerald-300 to-orange-300 bg-clip-text text-transparent">
                  GCMA
                </span>
              </h1>
              <p class="max-w-2xl text-base leading-7 text-slate-300 md:text-lg">
                Choisissez un module métier et passez d’une zone de production à une cellule qualité avec une interface orientée terrain, claire sous pression et prête pour la tablette.
              </p>
            </div>
          </div>

          <div class="kiosk-panel-soft flex flex-col items-start gap-4 rounded-[24px] p-4 backdrop-blur md:min-w-[300px]">
            <div class="flex items-center gap-3">
              <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/12 text-emerald-300 border border-emerald-400/15">
                <ShieldCheck :size="24" />
              </div>
              <div>
                <div class="text-sm uppercase tracking-[0.22em] text-slate-500">Session active</div>
                <div class="text-lg font-bold text-white">{{ store.fullName }}</div>
              </div>
            </div>
            <div class="grid w-full grid-cols-2 gap-3 text-sm text-slate-300">
              <div class="kiosk-tile rounded-2xl p-3">
                <div class="text-slate-500">Entreprise</div>
                <div class="mt-1 font-semibold">{{ store.operario?.company_abbr }}</div>
              </div>
              <div class="kiosk-tile rounded-2xl p-3">
                <div class="text-slate-500">Modules</div>
                <div class="mt-1 font-semibold">{{ moduleCountLabel }}</div>
              </div>
              <div class="kiosk-tile col-span-2 rounded-2xl p-3">
                <div class="text-slate-500">Profil kiosque</div>
                <div class="mt-1 font-semibold">{{ store.profileLabel }}</div>
              </div>
            </div>
            <Button
              label="Fermer la session"
              severity="secondary"
              class="!h-12 !w-full !rounded-2xl !border !border-slate-700 !bg-slate-900/80 !text-slate-200 hover:!bg-slate-800"
              @click="logout"
            >
              <template #icon>
                <LogOut :size="18" />
              </template>
            </Button>
          </div>
        </div>
      </div>

      <div class="grid gap-5 xl:grid-cols-[1.3fr_0.7fr]">
        <div class="grid gap-5 lg:grid-cols-2">
          <Card
            v-for="module in modules"
            :key="module.title"
            class="module-card kiosk-panel overflow-hidden rounded-[28px]"
          >
            <template #content>
              <div class="relative overflow-hidden rounded-[24px] border p-5 md:p-6" :class="module.border">
                <div class="absolute inset-0 bg-gradient-to-br" :class="module.accent" />
                <div class="relative z-10 flex h-full flex-col gap-5">
                  <div class="flex items-start justify-between gap-4">
                    <div class="space-y-3">
                      <Tag :value="module.badge" rounded class="kiosk-chip !rounded-full !px-3 !py-1 !text-[11px] !font-semibold !tracking-[0.24em] !text-slate-200" />
                      <div>
                        <h2 class="text-3xl font-black tracking-tight text-white">{{ module.title }}</h2>
                        <p class="mt-2 max-w-sm text-sm leading-6 text-slate-300">{{ module.subtitle }}</p>
                      </div>
                    </div>
                    <div class="kiosk-icon-shell flex h-16 w-16 items-center justify-center rounded-3xl shadow-inner shadow-black/30">
                      <component :is="module.icon" :size="30" />
                    </div>
                  </div>

                  <div class="grid grid-cols-2 gap-3 text-sm text-slate-300">
                    <div class="kiosk-tile rounded-2xl p-3">
                      <div class="text-slate-500">Mode</div>
                      <div class="mt-1 font-semibold">Tablette terrain</div>
                    </div>
                    <div class="kiosk-tile rounded-2xl p-3">
                      <div class="text-slate-500">Expérience</div>
                      <div class="mt-1 font-semibold">Fat-finger ready</div>
                    </div>
                  </div>

                  <Button
                    :label="module.cta"
                    class="!mt-auto !h-14 !rounded-2xl !border-0 !px-5 !text-sm !font-black !uppercase !tracking-[0.18em]"
                    :class="module.ctaClass"
                    @click="openModule(module.route)"
                  >
                    <template #icon>
                      <ArrowRight :size="18" />
                    </template>
                  </Button>
                </div>
              </div>
            </template>
          </Card>
        </div>

        <Card class="kiosk-panel overflow-hidden rounded-[28px]">
          <template #content>
            <div class="space-y-5">
              <div class="flex items-center gap-3">
                <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-orange-500/14 text-orange-200">
                  <Orbit :size="22" />
                </div>
                <div>
                  <div class="text-xs uppercase tracking-[0.24em] text-slate-500">Briefing</div>
                  <div class="text-2xl font-black text-white">Console métier</div>
                </div>
              </div>

              <div class="space-y-3 text-sm leading-6 text-slate-300">
                <p>
                  Chaque badge ouvre uniquement les modules autorisés par le profil ERPNext de l’employé. La séparation opérateur et laboratoire n’est plus seulement visuelle.
                </p>
                <p>
                  Le hub devient un point d’entrée métier: production pour le flux cadence opérateur, laboratoire pour le verdict qualité et la libération des lots.
                </p>
              </div>

              <div class="grid gap-3">
                <div class="rounded-2xl border border-teal-400/16 bg-teal-400/8 p-4">
                  <div class="text-xs uppercase tracking-[0.2em] text-teal-200">Production</div>
                  <div class="mt-1 text-sm text-slate-200">Validation matière, scans terrain, clôture native ERPNext.</div>
                </div>
                <div class="rounded-2xl border border-orange-400/16 bg-orange-400/8 p-4">
                  <div class="text-xs uppercase tracking-[0.2em] text-orange-200">Qualité</div>
                  <div class="mt-1 text-sm text-slate-200">Vue lots, verdict approuvé/rejeté, inspection liée aux documents natifs.</div>
                </div>
              </div>
            </div>
          </template>
        </Card>
      </div>
    </section>
  </div>
</template>