import { useAuth } from '@/providers/AuthProvider'
import Constants from 'expo-constants'
import { useEffect, useMemo, useRef, useState } from "react"
import { Image, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native"
import { SafeAreaView } from 'react-native-safe-area-context'

const logo = require("../../assets/images/logo.png")

function getNativeApiBase() {
  const anyConst: any = Constants
  const expoConfig = anyConst.expoConfig || anyConst.manifest || {}
  const hostUri: string = expoConfig.hostUri || expoConfig.debuggerHost || ""
  const host = hostUri.split(":")[0] || "127.0.0.1"
  return `http://${host}:3000`
}

const API_BASE =
  Platform.OS === "web" ? "http://127.0.0.1:3000" : getNativeApiBase()

const LINES = ['Gライン', 'Hライン', 'Iライン']

type Section = { title: string; items: string[] }

type PackageTask = {
  id: number
  lineName: string
  course: string
  productName: string
  total: number
  produced: number
  remaining: number
  step: number
}

function InfoCard({ title, value, sub, tone }: { title: string; value: string; sub?: string; tone?: "green" }) {
  const toneStyle = useMemo(() => {
    if (tone === "green") return { borderColor: "#147D37", backgroundColor: "#147D37" }
    return {}
  }, [tone])
  return (
    <View style={[styles.card, toneStyle]}>
      <Text style={styles.cardTitle}>{title}</Text>
      <Text style={styles.cardValue}>{value}</Text>
      {!!sub && <Text style={styles.cardSub}>{sub}</Text>}
    </View>
  )
}

function ActionButton({ label, color, onPress, disabled }: { label: string; color: "green" | "red"; onPress: () => void; disabled?: boolean }) {
  const bg = color === "green" ? "#147D37" : "#ef0c0cff"
  return (
    <Pressable
      onPress={onPress}
      disabled={!!disabled}
      style={({ pressed }) => [
        styles.actionBtn,
        { backgroundColor: bg, opacity: disabled ? 0.5 : pressed ? 0.9 : 1 },
      ]}
    >
      <Text style={styles.actionText}>{label}</Text>
    </Pressable>
  )
}

export default function PackageScreen() {
  const [sections, setSections] = useState<Section[]>([])
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [line, setLine] = useState<string>('Gライン')
  const [picked, setPicked] = useState<string | null>(null)
  const [tasks, setTasks] = useState<PackageTask[]>([])
  const [bannerMessage, setBannerMessage] = useState("")
  const hideRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [sending, setSending] = useState(false)
  const { logout } = useAuth()

  const current = useMemo(() => {
    if (!picked) return null
    return tasks.find(t => t.productName === picked) || null
  }, [tasks, picked])

  const hasTask = !!current
  const target = current?.total ?? 0
  const done = current?.produced ?? 0
  const remaining = current?.remaining ?? Math.max(target - done, 0)
  const step = current?.step ?? 0

  const NO_DATA = "_"
  const fmtNum = (n: number) => n.toLocaleString('ja-JP')

  const flash = (text: string) => {
    setBannerMessage(text)
    if (hideRef.current) clearTimeout(hideRef.current)
    hideRef.current = setTimeout(() => setBannerMessage(""), 1000)
  }

  useEffect(() => {
    return () => {
      if (hideRef.current) clearTimeout(hideRef.current)
    }
  }, [])

  const toggle = (title: string) =>
    setExpanded(prev => ({ ...prev, [title]: !prev[title] }))

  useEffect(() => {
    let active = true

    const buildSections = (list: PackageTask[]): Section[] => {
      const map = new Map<string, string[]>()
      list.forEach(t => {
        const key = t.course || "その他"
        const arr = map.get(key) || []
        if (!arr.includes(t.productName)) arr.push(t.productName)
        map.set(key, arr)
      })
      return Array.from(map.entries()).map(([title, items]) => ({ title, items }))
    }

    const fetchTasks = async () => {
      try {
        const r = await fetch(`${API_BASE}/package/tasks?line=${encodeURIComponent(line)}`)
        if (!r.ok) throw new Error(await r.text())
        const data = await r.json()
        if (!active) return

        const mapped: PackageTask[] = data.map((row: any) => ({
          id: row.id ?? row.梱包ID,
          lineName: row.ライン名 ?? "",
          course: row.クール名 ?? row.クール ?? "",
          productName: row.商品名 ?? "",
          total: Number(row.合計数 ?? 0),
          produced: Number(row.梱包数 ?? 0),
          remaining: Number(row.残数 ?? (Number(row.合計数 ?? 0) - Number(row.梱包数 ?? 0))),
          step: Number(row.カウント単位 ?? 0),
        }))

        setTasks(mapped)
        setSections(buildSections(mapped))
        setPicked(prev => {
          if (prev && mapped.some(t => t.productName === prev)) return prev
          return mapped.length ? mapped[0].productName : null
        })
      } catch (e) {
        if (!active) return
        setTasks([])
        setSections([])
        setPicked(null)
      }
    }

    fetchTasks()
    const timer = setInterval(fetchTasks, 3000)
    return () => {
      active = false
      clearInterval(timer)
    }
  }, [line])

  const canCount = hasTask && remaining > 0 && !sending

  const handleCount = async () => {
    if (!current) {
      alert('左のリストから商品を選択してください')
      return
    }
    if (remaining <= 0) {
      flash('完了しました')
      return
    }
    setSending(true)
    try {
      const r = await fetch(`${API_BASE}/package/count`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ taskId: current.id }),
      })
      const j = await r.json().catch(() => ({}))
      if (!r.ok) {
        alert(j?.message || `HTTP ${r.status}`)
        return
      }
      const newProduced = Number(j.producedCount ?? current.produced)
      setTasks(prev =>
        prev.map(t =>
          t.id === current.id
            ? { ...t, produced: newProduced, remaining: Math.max(t.total - newProduced, 0) }
            : t
        )
      )
      flash(j.message || "カウントしました")
    } catch (e) {
      alert("エラーが発生しました")
    } finally {
      setSending(false)
    }
  }

  const handleReset = async () => {
    if (!current) {
      alert('左のリストから商品を選択してください')
      return
    }
    setSending(true)
    try {
      const r = await fetch(`${API_BASE}/package/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ taskId: current.id }),
      })
      const j = await r.json().catch(() => ({}))
      if (!r.ok) {
        alert(j?.message || `HTTP ${r.status}`)
        return
      }
      const newProduced = Number(j.producedCount ?? 0)
      setTasks(prev =>
        prev.map(t =>
          t.id === current.id
            ? { ...t, produced: newProduced, remaining: Math.max(t.total - newProduced, 0) }
            : t
        )
      )
      flash(j.message || "リセットしました")
    } catch (e) {
      alert("エラーが発生しました")
    } finally {
      setSending(false)
    }
  }

  return (
    <SafeAreaView style={styles.root}>
      <View style={styles.header}>
        <View style={styles.brandRow}>
          <Image source={logo} style={{ width: 100, height: 50, resizeMode: "contain" }} />
          <View>
            <Text style={styles.appTitle}>おせち梱包管理</Text>
          </View>
          <Pressable
            onPress={logout}
            hitSlop={12}
            style={({ pressed }) => [styles.logoutBtn, pressed && { opacity: 0.85 }]}
          >
            <Text style={styles.logoutText}>ログアウト</Text>
          </Pressable>
        </View>

        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.lineBarContent}
        >
          {LINES.map(l => {
            const selected = line === l
            return (
              <Pressable
                key={l}
                onPress={() => {
                  setLine(l)
                  setPicked(null)
                  setBannerMessage("")
                }}
                style={[styles.lineChip, selected && styles.lineChipActive]}
              >
                <Text style={[styles.lineChipText, selected && styles.lineChipTextActive]}>
                  {l}
                </Text>
              </Pressable>
            )
          })}
        </ScrollView>
      </View>

      <View style={[styles.main, { flexDirection: "row" }]}>
        <View style={[styles.sidebar, { width: 160 }]}>
          <ScrollView contentContainerStyle={{ padding: 16 }}>
            {sections.map(sec => (
              <View key={sec.title} style={{ marginBottom: 16 }}>
                <Pressable onPress={() => toggle(sec.title)} style={styles.sectionHeader}>
                  <Text style={styles.sectionArrow}>
                    {expanded[sec.title] ?? true ? "▾" : "▸"}
                  </Text>
                  <Text style={styles.sectionTitle}>{sec.title}</Text>
                </Pressable>
                <View style={{ gap: 10, marginTop: 10 }}>
                  {(expanded[sec.title] ?? true) &&
                    sec.items.map(name => (
                      <Pressable
                        key={name}
                        onPress={() => {
                          setPicked(name)
                          setBannerMessage("")
                        }}
                        style={[
                          styles.pill,
                          { backgroundColor: picked === name ? "#147D37" : "#147D37" },
                        ]}
                      >
                        <Text style={styles.pillText}>{name}</Text>
                      </Pressable>
                    ))}
                </View>
              </View>
            ))}
          </ScrollView>
        </View>

        <ScrollView style={styles.content} contentContainerStyle={{ padding: 20 }}>
          {!picked ? (
            <View style={styles.empty}>
              <Text style={styles.emptyTitle}>左のリストから選択してください</Text>
            </View>
          ) : (
            <>
              <Text style={styles.sectionMainTitle}>{picked}</Text>

              <View style={[styles.row, { marginTop: 16 }]}>
                <InfoCard
                  title="合計数"
                  value={hasTask ? fmtNum(target) : NO_DATA}
                  sub="セット"
                  tone="green"
                />
                <InfoCard
                  title="進捗数"
                  value={hasTask ? fmtNum(done) : NO_DATA}
                  sub="セット"
                  tone="green"
                />
                <InfoCard
                  title="残数"
                  value={hasTask ? fmtNum(remaining) : NO_DATA}
                  sub="セット"
                  tone="green"
                />
                <InfoCard
                  title="カウント数/回"
                  value={hasTask ? fmtNum(step) : NO_DATA}
                  sub="セット"
                  tone="green"
                />
              </View>

              <View style={styles.banner}>
                <ActionButton
                  label="カウント"
                  color="red"
                  disabled={!canCount}
                  onPress={handleCount}
                />
                <ActionButton
                  label="リセット"
                  color="green"
                  disabled={!hasTask || sending}
                  onPress={handleReset}
                />
                <View style={styles.bannerMessage}>
                  <Text style={styles.bannerMsgText}>{bannerMessage || " "}</Text>
                </View>
              </View>
            </>
          )}
        </ScrollView>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: "#F1F5F9",
  },
  header: {
    paddingHorizontal: 24,
    paddingVertical: 16,
    backgroundColor: "#FFFFFF",
    borderBottomWidth: 1,
    borderBottomColor: "#E2E8F0",
  },
  appTitle: {
    fontSize: 24,
    fontWeight: "800",
  },
  main: { flex: 1 },
  sidebar: {
    backgroundColor: "#FFFFFF",
    borderRightWidth: 1,
    borderRightColor: "#E2E8F0",
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  sectionArrow: {
    fontSize: 18,
    color: "#0F172A",
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#0F172A",
    backgroundColor: "#BEBEBE",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 999,
  },
  pill: {
    alignSelf: "flex-start",
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 999,
  },
  pillText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "700",
  },
  content: { flex: 1 },
  sectionMainTitle: {
    fontSize: 22,
    fontWeight: "800",
  },
  row: {
    flexDirection: "row",
    gap: 16,
    marginTop: 12,
    flexWrap: "wrap",
  },
  card: {
    flexGrow: 1,
    minWidth: 220,
    padding: 18,
    borderRadius: 16,
    borderWidth: 1,
  },
  cardTitle: {
    fontSize: 14,
    color: "#FFFFFF",
  },
  cardValue: {
    fontSize: 28,
    fontWeight: "800",
    marginTop: 6,
    color: "#FFFFFF",
  },
  cardSub: {
    fontSize: 12,
    color: "#FFFFFF",
    marginTop: 2,
  },
  empty: {
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#FFFFFF",
    padding: 28,
    alignItems: "center",
    justifyContent: "center",
    minHeight: 260,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: "800",
    color: "#0F172A",
  },
  banner: {
    marginTop: 16,
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    paddingVertical: 18,
    paddingHorizontal: 16,
    alignSelf: "stretch",
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  brandRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  logoutText: {
    color: "#fff",
    fontWeight: "700",
  },
  logoutBtn: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    marginLeft: "auto",
    backgroundColor: "#147d37",
    borderRadius: 999,
  },
  actionBtn: {
    width: 200,
    paddingVertical: 16,
    borderRadius: 14,
    alignItems: "center",
  },
  actionText: {
    color: "#FFFFFF",
    fontSize: 18,
    fontWeight: "800",
    letterSpacing: 0.5,
  },
  bannerMessage: {
    flex: 1,
    backgroundColor: "#ffffff",
    borderRadius: 14,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 12,
    minHeight: 56,
  },
  bannerMsgText: {
    fontSize: 18,
    fontWeight: "800",
    color: "#ec2e0cff",
    letterSpacing: 0.5,
  },
  lineBarContent: {
    flexDirection: "row",
    alignItems: "center",
    columnGap: 8,
  },
  lineChip: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "#147d37",
    backgroundColor: "#ffffff",
    marginRight: 4,
  },
  lineChipActive: {
    backgroundColor: "#147d37",
  },
  lineChipText: {
    fontSize: 14,
    fontWeight: "600",
    color: "#147d37",
  },
  lineChipTextActive: {
    color: "#ffffff",
  },
})
