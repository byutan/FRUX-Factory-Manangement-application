import Constants from 'expo-constants';
import { useRouter } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import type { StyleProp, ViewStyle } from 'react-native';
import {
  FlatList,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

function getNativeApiBase() {
  const anyConst: any = Constants;
  const expoConfig = anyConst.expoConfig || anyConst.manifest || {};
  const hostUri: string = expoConfig.hostUri || expoConfig.debuggerHost || "";
  const host = hostUri.split(":")[0] || "127.0.0.1";
  return `http://${host}:3000`;
}
const API_BASE = Platform.OS === "web" ? "http://127.0.0.1:3000" : getNativeApiBase();

const GREEN = '#157f3d';
const GREEN_DARK = '#0f5f2d';
const BORDER = '#d1d5db';
const MUTED = '#9b9b9b';
const LINE = '#e5e5e5';

const COOL_OPTIONS = ['1', '2', '3', '4', '5'];
const MORITSUKE_OPTIONS = ['A', 'B', 'C', 'D', 'E', 'F'];
const WEEK_LABELS = ['日', '月', '火', '水', '木', '金', '土'];
const TIME_ITEM_H = 52;

type TimeValue = { h: number; m: number; s: number };
type Target = 'start' | 'end';

const pad2 = (n: number) => String(n).padStart(2, '0');

const fmtDate = (d: Date | null) =>
  d ? `${d.getFullYear()}/${pad2(d.getMonth() + 1)}/${pad2(d.getDate())}` : '';

const fmtTime = (t: TimeValue | null) =>
  t ? `${pad2(t.h)}:${pad2(t.m)}:${pad2(t.s)}` : '';

const toSec = (t: TimeValue) => t.h * 3600 + t.m * 60 + t.s;

const dayKey = (d: Date) => d.getFullYear() * 10000 + d.getMonth() * 100 + d.getDate();

const sameDay = (a: Date, b: Date) => dayKey(a) === dayKey(b);

const range = (count: number, from = 0) => Array.from({ length: count }, (_, i) => i + from);

function buildMonthCells(year: number, month: number): (number | null)[] {
  const startWeekday = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (number | null)[] = [];
  for (let i = 0; i < startWeekday; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}

type SelectFieldProps = {
  value: string | null;
  options: string[];
  title: string;
  placeholder?: string;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
  onChange: (v: string) => void;
};

function SelectField({
  value,
  options,
  title,
  placeholder = '選択',
  disabled = false,
  style,
  onChange,
}: SelectFieldProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Pressable
        disabled={disabled}
        onPress={() => setOpen(true)}
        style={({ pressed }) => [
          styles.pickBox,
          style,
          disabled && styles.boxDisabled,
          pressed && !disabled && styles.boxPressed,
        ]}
      >
        <Text
          style={[
            styles.boxTxt,
            !value && styles.placeholderTxt,
            disabled && styles.txtDisabled,
          ]}
          numberOfLines={1}
        >
          {value ?? placeholder}
        </Text>
        <Text style={[styles.caret, disabled && styles.txtDisabled]}>▼</Text>
      </Pressable>

      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <View style={styles.modalRoot}>
          <Pressable style={StyleSheet.absoluteFill} onPress={() => setOpen(false)} />
          <View style={styles.sheet}>
            <Text style={styles.sheetTitle}>{title}</Text>

            <View style={styles.optionWrap}>
              {options.map((opt) => {
                const on = opt === value;
                return (
                  <Pressable
                    key={opt}
                    onPress={() => {
                      onChange(opt);
                      setOpen(false);
                    }}
                    style={({ pressed }) => [
                      styles.optionChip,
                      on && styles.optionChipOn,
                      pressed && !on && styles.boxPressed,
                    ]}
                  >
                    <Text style={[styles.optionTxt, on && styles.optionTxtOn]}>{opt}</Text>
                  </Pressable>
                );
              })}
            </View>

            <View style={styles.sheetActions}>
              <Pressable onPress={() => setOpen(false)} style={styles.ghostBtn}>
                <Text style={styles.ghostTxt}>キャンセル</Text>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
    </>
  );
}

type CalendarModalProps = {
  visible: boolean;
  title: string;
  value: Date | null;
  onClose: () => void;
  onSelect: (d: Date) => void;
};

function CalendarModal({ visible, title, value, onClose, onSelect }: CalendarModalProps) {
  const [cursor, setCursor] = useState(() => new Date());

  useEffect(() => {
    if (!visible) return;
    const base = value ?? new Date();
    setCursor(new Date(base.getFullYear(), base.getMonth(), 1));
  }, [visible, value]);

  const cells = useMemo(
    () => buildMonthCells(cursor.getFullYear(), cursor.getMonth()),
    [cursor]
  );

  const today = new Date();
  const shiftMonth = (delta: number) =>
    setCursor((c) => new Date(c.getFullYear(), c.getMonth() + delta, 1));

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.modalRoot}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} />
        <View style={[styles.sheet, styles.calSheet]}>
          <Text style={styles.sheetTitle}>{title}</Text>

          <View style={styles.calHeader}>
            <Pressable onPress={() => shiftMonth(-1)} style={styles.calNavBtn}>
              <Text style={styles.calNavTxt}>‹</Text>
            </Pressable>
            <Text style={styles.calTitle}>
              {cursor.getFullYear()}年 {cursor.getMonth() + 1}月
            </Text>
            <Pressable onPress={() => shiftMonth(1)} style={styles.calNavBtn}>
              <Text style={styles.calNavTxt}>›</Text>
            </Pressable>
          </View>

          <View style={styles.calWeekRow}>
            {WEEK_LABELS.map((w, i) => (
              <View key={w} style={styles.calWeekCell}>
                <Text
                  style={[
                    styles.calWeekTxt,
                    i === 0 && styles.sunTxt,
                    i === 6 && styles.satTxt,
                  ]}
                >
                  {w}
                </Text>
              </View>
            ))}
          </View>

          <View style={styles.calGrid}>
            {cells.map((day, i) => {
              if (day === null) return <View key={`empty-${i}`} style={styles.calCell} />;

              const d = new Date(cursor.getFullYear(), cursor.getMonth(), day);
              const selected = value !== null && sameDay(d, value);
              const isToday = sameDay(d, today);
              const weekday = i % 7;

              return (
                <View key={day} style={styles.calCell}>
                  <Pressable
                    onPress={() => onSelect(d)}
                    style={({ pressed }) => [
                      styles.calDay,
                      isToday && !selected && styles.calDayToday,
                      selected && styles.calDayOn,
                      pressed && !selected && styles.boxPressed,
                    ]}
                  >
                    <Text
                      style={[
                        styles.calDayTxt,
                        weekday === 0 && styles.sunTxt,
                        weekday === 6 && styles.satTxt,
                        selected && styles.calDayTxtOn,
                      ]}
                    >
                      {day}
                    </Text>
                  </Pressable>
                </View>
              );
            })}
          </View>

          <View style={styles.sheetActions}>
            <Pressable onPress={() => onSelect(new Date())} style={styles.ghostBtn}>
              <Text style={styles.ghostTxt}>今日</Text>
            </Pressable>
            <Pressable onPress={onClose} style={styles.ghostBtn}>
              <Text style={styles.ghostTxt}>キャンセル</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}

type TimeColumnProps = {
  label: string;
  data: number[];
  selected: number;
  onSelect: (n: number) => void;
};

function TimeColumn({ label, data, selected, onSelect }: TimeColumnProps) {
  return (
    <View style={styles.timeCol}>
      <Text style={styles.timeColLabel}>{label}</Text>
      <FlatList
        data={data}
        style={styles.timeList}
        keyExtractor={(n) => String(n)}
        showsVerticalScrollIndicator={false}
        initialNumToRender={10}
        getItemLayout={(_, index) => ({
          length: TIME_ITEM_H,
          offset: TIME_ITEM_H * index,
          index,
        })}
        initialScrollIndex={Math.max(0, selected - 2)}
        renderItem={({ item }) => {
          const on = item === selected;
          return (
            <Pressable
              onPress={() => onSelect(item)}
              style={[styles.timeItem, on && styles.timeItemOn]}
            >
              <Text style={[styles.timeItemTxt, on && styles.timeItemTxtOn]}>{pad2(item)}</Text>
            </Pressable>
          );
        }}
      />
    </View>
  );
}

type TimeModalProps = {
  visible: boolean;
  title: string;
  value: TimeValue | null;
  onClose: () => void;
  onConfirm: (t: TimeValue) => void;
};

function TimeModal({ visible, title, value, onClose, onConfirm }: TimeModalProps) {
  const [draft, setDraft] = useState<TimeValue>({ h: 8, m: 0, s: 0 });

  useEffect(() => {
    if (visible) setDraft(value ?? { h: 8, m: 0, s: 0 });
  }, [visible, value]);

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.modalRoot}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} />
        <View style={[styles.sheet, styles.timeSheet]}>
          <Text style={styles.sheetTitle}>{title}</Text>
          <Text style={styles.timePreview}>{fmtTime(draft)}</Text>

          <View style={styles.timeRow}>
            <TimeColumn
              label="時"
              data={range(24)}
              selected={draft.h}
              onSelect={(h) => setDraft((d) => ({ ...d, h }))}
            />
            <TimeColumn
              label="分"
              data={range(60)}
              selected={draft.m}
              onSelect={(m) => setDraft((d) => ({ ...d, m }))}
            />
            <TimeColumn
              label="秒"
              data={range(60)}
              selected={draft.s}
              onSelect={(s) => setDraft((d) => ({ ...d, s }))}
            />
          </View>

          <View style={styles.sheetActions}>
            <Pressable onPress={onClose} style={styles.ghostBtn}>
              <Text style={styles.ghostTxt}>キャンセル</Text>
            </Pressable>
            <Pressable onPress={() => onConfirm(draft)} style={styles.smallBtn}>
              <Text style={styles.smallBtnTxt}>決定</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}

export default function MasterInput() {
  const router = useRouter();

  const [productName, setProductName] = useState('');
  const [totalCount, setTotalCount] = useState('');

  const [cool, setCool] = useState<string | null>(null);
  const [lineCode, setLineCode] = useState('');
  const [moritsuke, setMoritsuke] = useState<string | null>(null);

  const [startDate, setStartDate] = useState<Date | null>(null);
  const [endDate, setEndDate] = useState<Date | null>(null);
  const [startTime, setStartTime] = useState<TimeValue | null>(null);
  const [endTime, setEndTime] = useState<TimeValue | null>(null);

  const [dateTarget, setDateTarget] = useState<Target | null>(null);
  const [timeTarget, setTimeTarget] = useState<Target | null>(null);
  const [breakTime, setBreakTime] = useState('60');

  const [feedback, setFeedback] = useState<{ msg: string; isError: boolean } | null>(null);

  const coolSelected = cool !== null;
  const lineCodeFilled = lineCode.trim().length > 0;

  const onChangeCool = (v: string) => {
    if (v === cool) return;
    setCool(v);
    setLineCode('');
    setMoritsuke(null);
  };

  const onChangeLineCode = (v: string) => {
    setLineCode(v);
    if (v.trim().length === 0) setMoritsuke(null);
  };

  const goBack = () => {
  if (router.canGoBack()) {
    router.back();
  } else {
    router.replace('/auth/login');
  }
};

  const warn = (msg: string) => setFeedback({ msg, isError: true });

  const resetForm = () => {
    setProductName('');
    setTotalCount('');
    setCool(null);
    setLineCode('');
    setMoritsuke(null);
    setStartDate(null);
    setEndDate(null);
    setStartTime(null);
    setEndTime(null);
  };

  const handleSave = async () => {
    setFeedback(null);
    
    const total = Number(totalCount);
    
    if (!productName.trim()) return warn('商品名を入力してください。');
    if (!Number.isInteger(total) || total <= 0) return warn('合計数を正しく入力してください。');
    if (!cool) return warn('クールを選択してください。');
    if (!lineCode.trim()) return warn('ラインコードを入力してください。');
    if (!moritsuke) return warn('盛付ラインを選択してください。');
    if (!startDate || !endDate) return warn('生産開始日と終了日を選択してください。');
    if (dayKey(endDate) < dayKey(startDate)) return warn('終了日は開始日以降にしてください。');
    if (!startTime || !endTime) return warn('予定開始時刻と終了時刻を選択してください。');
    if (sameDay(startDate, endDate) && toSec(endTime) <= toSec(startTime)) {
      return warn('同じ日の場合、終了時刻は開始時刻より後にしてください。');
    }
    
    const payload = {
      商品名: productName.trim(),
      クール: cool,
      ラインコード: Number(lineCode.trim()),
      盛付ライン: `${moritsuke}ライン`,
      合計数: total,
      生産開始日: fmtDate(startDate).replace(/\//g, '-'), 
      予定開始時刻: fmtTime(startTime),
      生産終了日: fmtDate(endDate).replace(/\//g, '-'),  
      予定終了時刻: fmtTime(endTime),
      休憩min: Number(breakTime) || 60, 
    };

    try {
      const res = await fetch(`${API_BASE}/api/production-data`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        warn(data.message || 'サーバーエラーが発生しました。');
        return;
      }

      resetForm();
      setFeedback({ msg: '保存に成功しました！', isError: false });

    } catch (err) {
      console.log('handleSave fetch error:', err);
      warn('サーバーエラー (接続できません)');
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.screen}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.card}>
        <View style={styles.headerRow}>
          <View style={styles.titleBox}>
            <Text style={styles.titleTxt}>商品情報入力</Text>
          </View>
          <Pressable
            onPress={goBack}
            style={({ pressed }) => [styles.btn, pressed && styles.btnPressed]}
          >
            <Text style={styles.btnTxt}>戻る</Text>
          </Pressable>
        </View>

        <ScrollView
          style={styles.formScroll}
          contentContainerStyle={styles.form}
          keyboardShouldPersistTaps="handled"
        >
          {feedback && (
            <View style={[styles.feedbackBox, feedback.isError ? styles.feedbackError : styles.feedbackSuccess]}>
              <Text style={[styles.feedbackTxt, feedback.isError ? styles.feedbackTxtError : styles.feedbackTxtSuccess]}>
                {feedback.msg}
              </Text>
            </View>
          )}

          {/* HÀNG 1: Sử dụng flex 1 cho 2 input và cố định độ dài label */}
          <View style={styles.row}>
            <Text style={[styles.label, styles.labelLead]}>商品名</Text>
            <TextInput
              style={[styles.input, { flex: 1 }]}
              value={productName}
              onChangeText={setProductName}
              placeholder="商品名を入力"
              placeholderTextColor={MUTED}
              selectionColor={GREEN}
              returnKeyType="next"
            />

            <Text style={[styles.label, styles.middleWrap]}>合計数</Text>
            <TextInput
              style={[styles.input, { flex: 1 }]}
              value={totalCount}
              onChangeText={(t) => setTotalCount(t.replace(/[^0-9]/g, ''))}
              keyboardType="number-pad"
              placeholder="0"
              placeholderTextColor={MUTED}
              selectionColor={GREEN}
              returnKeyType="next"
            />
          </View>

          <View style={styles.row}>
            <Text style={[styles.label, styles.labelLead]}>クール</Text>
            <SelectField
              title="クールを選択 (1〜5)"
              value={cool}
              options={COOL_OPTIONS}
              onChange={onChangeCool}
              style={styles.selectSm}
            />

            <Text style={[styles.arrow, !coolSelected && styles.arrowOff]}>→</Text>

            <Text style={[styles.label, !coolSelected && styles.txtDisabled]}>ラインコード</Text>
            <TextInput
              style={[styles.input, { flex: 1 }, !coolSelected && styles.boxDisabled]}
              value={lineCode}
              onChangeText={onChangeLineCode}
              editable={coolSelected}
              placeholder={coolSelected ? '例: L-001' : 'クールを先に選択'}
              placeholderTextColor={MUTED}
              selectionColor={GREEN}
              autoCapitalize="characters"
              autoCorrect={false}
              returnKeyType="next"
            />

            <Text style={[styles.arrow, !lineCodeFilled && styles.arrowOff]}>→</Text>

            <Text style={[styles.label, !lineCodeFilled && styles.txtDisabled]}>盛付ライン</Text>
            <SelectField
              title="盛付ラインを選択 (A〜F)"
              value={moritsuke}
              options={MORITSUKE_OPTIONS}
              disabled={!lineCodeFilled}
              onChange={setMoritsuke}
              style={styles.selectSm}
            />
          </View>

          {/* HÀNG 3: Bọc label giữa vào middleWrap */}
          <View style={styles.row}>
            <Text style={[styles.label, styles.labelLead]}>生産開始日</Text>
            <Pressable
              onPress={() => setDateTarget('start')}
              style={({ pressed }) => [styles.pickBox, { flex: 1 }, pressed && styles.boxPressed]}
            >
              <Text style={[styles.boxTxt, !startDate && styles.placeholderTxt]}>
                {startDate ? fmtDate(startDate) : 'YYYY/MM/DD'}
              </Text>
            </Pressable>

            <View style={styles.middleWrap}>
              <Text style={styles.tilde}>～</Text>
              <Text style={styles.label}>終了日</Text>
            </View>

            <Pressable
              onPress={() => setDateTarget('end')}
              style={({ pressed }) => [styles.pickBox, { flex: 1 }, pressed && styles.boxPressed]}
            >
              <Text style={[styles.boxTxt, !endDate && styles.placeholderTxt]}>
                {endDate ? fmtDate(endDate) : 'YYYY/MM/DD'}
              </Text>
            </Pressable>
          </View>

          <View style={styles.row}>
            <Text style={[styles.label, styles.labelLead]}>予定開始時刻</Text>
            <Pressable
              onPress={() => setTimeTarget('start')}
              style={({ pressed }) => [styles.pickBox, { flex: 1 }, pressed && styles.boxPressed]}
            >
              <Text style={[styles.boxTxt, !startTime && styles.placeholderTxt]}>
                {startTime ? fmtTime(startTime) : 'HH:mm:ss'}
              </Text>
            </Pressable>

            <View style={styles.middleWrap}>
              <Text style={styles.tilde}>～</Text>
              <Text style={styles.label}>終了時刻</Text>
            </View>

            <Pressable
              onPress={() => setTimeTarget('end')}
              style={({ pressed }) => [styles.pickBox, { flex: 1 }, pressed && styles.boxPressed]}
            >
              <Text style={[styles.boxTxt, !endTime && styles.placeholderTxt]}>
                {endTime ? fmtTime(endTime) : 'HH:mm:ss'}
              </Text>
            </Pressable>
          </View>
        </ScrollView>

        <View style={styles.footerRow}>
          <Pressable
            onPress={handleSave}
            style={({ pressed }) => [styles.btn, styles.saveBtn, pressed && styles.btnPressed]}
          >
            <Text style={styles.btnTxt}>保存</Text>
          </Pressable>
        </View>
      </View>

      <CalendarModal
        visible={dateTarget !== null}
        title={dateTarget === 'end' ? '終了日を選択' : '生産開始日を選択'}
        value={dateTarget === 'end' ? endDate : startDate}
        onClose={() => setDateTarget(null)}
        onSelect={(d) => {
          if (dateTarget === 'end') setEndDate(d);
          else setStartDate(d);
          setDateTarget(null);
        }}
      />

      <TimeModal
        visible={timeTarget !== null}
        title={timeTarget === 'end' ? '終了時刻を選択' : '予定開始時刻を選択'}
        value={timeTarget === 'end' ? endTime : startTime}
        onClose={() => setTimeTarget(null)}
        onConfirm={(t) => {
          if (timeTarget === 'end') setEndTime(t);
          else setStartTime(t);
          setTimeTarget(null);
        }}
      />
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#f3f3f3',
    paddingVertical: 16,
    paddingHorizontal: 16,
  },
  card: {
    flex: 1,
    backgroundColor: '#fff',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: BORDER,
    paddingVertical: 20,
    paddingHorizontal: 24,
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 10,
    elevation: 2,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: LINE,
  },
  titleBox: {
    borderWidth: 1,
    borderColor: BORDER,
    borderRadius: 12,
    paddingVertical: 6,
    paddingHorizontal: 22,
  },
  titleTxt: {
    fontSize: 32,
    fontWeight: '700',
    color: '#111',
    letterSpacing: 1,
  },
  btn: {
    backgroundColor: GREEN,
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 30,
    minWidth: 120,
    alignItems: 'center',
    justifyContent: 'center',
  },
  btnPressed: { backgroundColor: GREEN_DARK },
  btnTxt: { color: '#fff', fontSize: 24, fontWeight: '700' },
  saveBtn: { minWidth: 180, paddingVertical: 12 },

  formScroll: { flex: 1 },
  form: { paddingTop: 16, paddingBottom: 14, gap: 20 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 16 },

  label: { fontSize: 20, fontWeight: '600', color: '#333' },
  labelLead: { width: 145 },
  
  /* Cố định chiều rộng cụm nhãn ở giữa để chia đều không gian flex 1 hai bên */
  middleWrap: {
    width: 140,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    textAlign: 'center',
  },

  input: {
    height: 54,
    borderWidth: 1,
    borderColor: BORDER,
    borderRadius: 12,
    paddingHorizontal: 16,
    fontSize: 20,
    color: '#111',
    backgroundColor: '#fff',
  },
  pickBox: {
    height: 54,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
    borderWidth: 1,
    borderColor: BORDER,
    borderRadius: 12,
    paddingHorizontal: 16,
    backgroundColor: '#fff',
  },
  boxTxt: { fontSize: 20, color: '#111', fontWeight: '500' },
  placeholderTxt: { color: MUTED, fontWeight: '400' },
  boxPressed: { backgroundColor: '#f9f9f9' },
  boxDisabled: { backgroundColor: '#f4f4f4', borderColor: '#e5e5e5', color: MUTED },
  txtDisabled: { color: MUTED },
  caret: { fontSize: 16, color: MUTED },
  selectSm: { width: 140 },

  arrow: { fontSize: 24, fontWeight: '700', color: MUTED, paddingHorizontal: 2 },
  arrowOff: { color: '#e5e5e5' },
  tilde: { fontSize: 24, fontWeight: '700', color: '#666', paddingHorizontal: 4 },

  footerRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: LINE,
  },

  feedbackBox: {
    padding: 14,
    borderRadius: 10,
    marginBottom: 8,
    borderWidth: 1,
  },
  feedbackError: {
    backgroundColor: '#fef2f2',
    borderColor: '#fca5a5',
  },
  feedbackSuccess: {
    backgroundColor: '#f0fdf4',
    borderColor: '#86efac',
  },
  feedbackTxt: {
    fontSize: 18,
    fontWeight: '600',
    textAlign: 'center',
  },
  feedbackTxtError: {
    color: '#dc2626',
  },
  feedbackTxtSuccess: {
    color: '#16a34a',
  },

  modalRoot: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  sheet: {
    backgroundColor: '#fff',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: BORDER,
    paddingVertical: 22,
    paddingHorizontal: 24,
    minWidth: 340,
  },
  sheetTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#111',
    textAlign: 'center',
    marginBottom: 18,
  },
  sheetActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 12,
    marginTop: 20,
  },
  ghostBtn: {
    paddingVertical: 10,
    paddingHorizontal: 22,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: BORDER,
  },
  ghostTxt: { fontSize: 18, fontWeight: '600', color: '#333' },
  smallBtn: {
    backgroundColor: GREEN,
    paddingVertical: 12,
    paddingHorizontal: 28,
    borderRadius: 12,
  },
  smallBtnTxt: { color: '#fff', fontSize: 18, fontWeight: '700' },

  optionWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    justifyContent: 'center',
    maxWidth: 420,
  },
  optionChip: {
    minWidth: 88,
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: BORDER,
    alignItems: 'center',
  },
  optionChipOn: { backgroundColor: GREEN, borderColor: GREEN },
  optionTxt: { fontSize: 24, fontWeight: '600', color: '#333' },
  optionTxtOn: { color: '#fff' },

  calSheet: { width: 440 },
  calHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  calNavBtn: {
    width: 50,
    height: 44,
    borderRadius: 8,
    backgroundColor: GREEN,
    alignItems: 'center',
    justifyContent: 'center',
  },
  calNavTxt: { color: '#fff', fontSize: 26, fontWeight: '700', lineHeight: 30 },
  calTitle: { fontSize: 22, fontWeight: '700', color: '#111' },
  calWeekRow: { flexDirection: 'row', marginBottom: 4 },
  calWeekCell: { width: '14.2857%', alignItems: 'center', paddingVertical: 4 },
  calWeekTxt: { fontSize: 16, fontWeight: '700', color: '#555' },
  calGrid: { flexDirection: 'row', flexWrap: 'wrap' },
  calCell: { width: '14.2857%', height: 48, padding: 3 },
  calDay: {
    flex: 1,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  calDayOn: { backgroundColor: GREEN },
  calDayToday: { borderWidth: 1, borderColor: GREEN },
  calDayTxt: { fontSize: 18, fontWeight: '600', color: '#111' },
  calDayTxtOn: { color: '#fff' },
  sunTxt: { color: '#c62828' },
  satTxt: { color: '#1565c0' },

  timeSheet: { width: 400 },
  timePreview: {
    fontSize: 36,
    fontWeight: '700',
    color: GREEN,
    textAlign: 'center',
    marginTop: -8,
    marginBottom: 14,
    letterSpacing: 1,
  },
  timeRow: { flexDirection: 'row', gap: 12 },
  timeCol: { flex: 1, alignItems: 'center' },
  timeColLabel: { fontSize: 16, fontWeight: '700', color: '#555', marginBottom: 6 },
  timeList: {
    height: 240,
    width: '100%',
    borderWidth: 1,
    borderColor: '#e5e5e5',
    borderRadius: 10,
  },
  timeItem: { height: TIME_ITEM_H, alignItems: 'center', justifyContent: 'center' },
  timeItemOn: { backgroundColor: GREEN },
  timeItemTxt: { fontSize: 24, fontWeight: '500', color: '#111' },
  timeItemTxtOn: { color: '#fff' },
});