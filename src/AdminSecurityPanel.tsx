import { useEffect, useState, type FormEvent } from "react";
import { KeyRound, ShieldCheck, X } from "lucide-react";

import {
  AUTH_SESSION_EVENT,
  confirmAdminPasswordChange,
  requestAdminPasswordChange,
  type AuthSession,
  type SecurityChallenge,
} from "./services/auth";


type Step = "password" | "mfa" | "complete";

export default function AdminSecurityPanel() {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<Step>("password");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [code, setCode] = useState("");
  const [challenge, setChallenge] = useState<SecurityChallenge | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    const handleSession = (event: Event) => {
      const customEvent = event as CustomEvent<AuthSession>;
      setSession(customEvent.detail);
    };
    window.addEventListener(AUTH_SESSION_EVENT, handleSession);
    return () => window.removeEventListener(AUTH_SESSION_EVENT, handleSession);
  }, []);

  if (!session || session.account.role !== "admin") return null;

  function resetForm() {
    setStep("password");
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setCode("");
    setChallenge(null);
    setError("");
    setSuccessMessage("");
    setBusy(false);
  }

  function closePanel() {
    if (busy) return;
    setOpen(false);
    resetForm();
  }

  async function handleRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (newPassword !== confirmPassword) {
      setError("A confirmação da nova palavra-passe não coincide.");
      return;
    }
    if (newPassword.length < 12) {
      setError("Use pelo menos 12 caracteres na nova palavra-passe.");
      return;
    }

    setBusy(true);
    try {
      const nextChallenge = await requestAdminPasswordChange(session.accessToken, currentPassword);
      setChallenge(nextChallenge);
      setStep("mfa");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível iniciar a alteração.");
    } finally {
      setBusy(false);
    }
  }

  async function handleConfirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!challenge) {
      setError("O pedido de segurança expirou. Inicie novamente.");
      setStep("password");
      return;
    }

    setBusy(true);
    setError("");
    try {
      const result = await confirmAdminPasswordChange(session.accessToken, {
        challengeId: challenge.id,
        code,
        currentPassword,
        newPassword,
        confirmPassword,
      });
      setSuccessMessage(result.message);
      setStep("complete");
    } catch (confirmError) {
      setError(confirmError instanceof Error ? confirmError.message : "Não foi possível confirmar a alteração.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-5 right-5 z-40 inline-flex items-center gap-2 rounded-full border border-white/10 bg-[#111719] px-4 py-3 text-sm font-semibold text-white shadow-2xl shadow-black/30 transition hover:border-amber-400/40 hover:bg-[#171d20]"
        title="Administrador · Segurança"
      >
        <ShieldCheck size={18} className="text-amber-400" />
        Segurança
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Segurança do administrador">
          <section className="w-full max-w-lg overflow-hidden rounded-[28px] border border-white/10 bg-[#0b1012] text-white shadow-2xl">
            <header className="flex items-start justify-between gap-4 border-b border-white/10 px-6 py-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-400">Administrador → Segurança</p>
                <h2 className="mt-2 text-2xl font-semibold">Alterar palavra-passe</h2>
                <p className="mt-2 text-sm leading-6 text-[#a8a29e]">A alteração exige a palavra-passe atual e um novo código MFA.</p>
              </div>
              <button type="button" onClick={closePanel} disabled={busy} className="rounded-xl border border-white/10 p-2 text-[#d6d3d1] hover:bg-white/10 disabled:opacity-50" aria-label="Fechar">
                <X size={18} />
              </button>
            </header>

            <div className="p-6">
              {step === "password" && (
                <form onSubmit={handleRequest}>
                  <label className="block text-sm font-medium text-[#d6d3d1]">
                    Palavra-passe atual
                    <input
                      type="password"
                      autoComplete="current-password"
                      value={currentPassword}
                      onChange={(event) => setCurrentPassword(event.target.value)}
                      className="mt-2 h-11 w-full rounded-xl border border-white/10 bg-white/[0.06] px-3 text-white outline-none focus:border-amber-400"
                      required
                    />
                  </label>

                  <label className="mt-4 block text-sm font-medium text-[#d6d3d1]">
                    Nova palavra-passe
                    <input
                      type="password"
                      autoComplete="new-password"
                      value={newPassword}
                      onChange={(event) => setNewPassword(event.target.value)}
                      className="mt-2 h-11 w-full rounded-xl border border-white/10 bg-white/[0.06] px-3 text-white outline-none focus:border-amber-400"
                      minLength={12}
                      required
                    />
                  </label>

                  <label className="mt-4 block text-sm font-medium text-[#d6d3d1]">
                    Confirmar nova palavra-passe
                    <input
                      type="password"
                      autoComplete="new-password"
                      value={confirmPassword}
                      onChange={(event) => setConfirmPassword(event.target.value)}
                      className="mt-2 h-11 w-full rounded-xl border border-white/10 bg-white/[0.06] px-3 text-white outline-none focus:border-amber-400"
                      minLength={12}
                      required
                    />
                  </label>

                  <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.04] p-4 text-xs leading-5 text-[#a8a29e]">
                    Use 12+ caracteres com maiúscula, minúscula, número e símbolo. A palavra-passe nunca é guardada em texto simples.
                  </div>

                  {error && <p className="mt-4 rounded-xl border border-red-400/20 bg-red-500/10 p-3 text-sm text-red-200">{error}</p>}

                  <button type="submit" disabled={busy} className="mt-5 inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-amber-400 px-5 text-sm font-semibold text-black hover:bg-amber-300 disabled:opacity-50">
                    <KeyRound size={17} />
                    {busy ? "A validar…" : "Validar e enviar código MFA"}
                  </button>
                </form>
              )}

              {step === "mfa" && challenge && (
                <form onSubmit={handleConfirm}>
                  <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-4 text-sm leading-6 text-emerald-100">
                    {challenge.deliveryHint}
                    {challenge.developmentCode && (
                      <span className="mt-3 block rounded-xl border border-emerald-300/20 bg-black/20 px-4 py-3 text-center text-xl font-semibold tracking-[0.28em] text-white">
                        {challenge.developmentCode}
                      </span>
                    )}
                  </div>

                  <label className="mt-5 block text-sm font-medium text-[#d6d3d1]">
                    Código de segurança
                    <input
                      type="text"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      maxLength={6}
                      value={code}
                      onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                      className="mt-2 h-12 w-full rounded-xl border border-white/10 bg-white/[0.06] px-3 text-center text-lg font-semibold tracking-[0.32em] text-white outline-none focus:border-amber-400"
                      placeholder="000000"
                      required
                    />
                  </label>

                  {error && <p className="mt-4 rounded-xl border border-red-400/20 bg-red-500/10 p-3 text-sm text-red-200">{error}</p>}

                  <button type="submit" disabled={busy || code.length !== 6} className="mt-5 h-11 w-full rounded-xl bg-amber-400 px-5 text-sm font-semibold text-black hover:bg-amber-300 disabled:opacity-50">
                    {busy ? "A confirmar…" : "Confirmar alteração"}
                  </button>
                  <button type="button" disabled={busy} onClick={() => { setStep("password"); setCode(""); setChallenge(null); setError(""); }} className="mt-2 h-10 w-full rounded-xl border border-white/10 text-sm font-semibold text-[#d6d3d1] hover:bg-white/5 disabled:opacity-50">
                    Voltar
                  </button>
                </form>
              )}

              {step === "complete" && (
                <div className="text-center">
                  <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-400/10 text-emerald-300">
                    <ShieldCheck size={28} />
                  </span>
                  <h3 className="mt-4 text-xl font-semibold">Credenciais atualizadas</h3>
                  <p className="mt-2 text-sm leading-6 text-[#a8a29e]">{successMessage}</p>
                  <p className="mt-3 text-xs leading-5 text-[#78716c]">As sessões anteriores foram invalidadas por segurança.</p>
                  <button type="button" onClick={() => window.location.reload()} className="mt-6 h-11 w-full rounded-xl bg-white px-5 text-sm font-semibold text-black hover:bg-amber-50">
                    Voltar ao login
                  </button>
                </div>
              )}
            </div>
          </section>
        </div>
      )}
    </>
  );
}
