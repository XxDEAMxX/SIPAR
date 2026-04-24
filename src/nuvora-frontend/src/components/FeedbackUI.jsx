import { CheckCircle2, LoaderCircle, X } from 'lucide-react'
import { toneClasses } from '../utils/sipar'

export function ToastStack({ toasts }) {
  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`glass-card flex min-w-[280px] items-start gap-2 border px-3 py-2 text-sm animate-fade-up ${toneClasses(toast.tone)}`}
          role="status"
          aria-live="polite"
        >
          {toast.tone === 'success' ? (
            <CheckCircle2 size={16} />
          ) : toast.tone === 'error' ? (
            <X size={16} />
          ) : (
            <LoaderCircle size={16} />
          )}
          <div>
            <p className="font-semibold">{toast.title}</p>
            <p className="text-xs text-sipar-muted">{toast.message}</p>
          </div>
        </div>
      ))}
    </div>
  )
}

export function ConfirmModal({ title, description, confirmText, onConfirm, onCancel }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/65 px-4 backdrop-blur-sm">
      <div className="glass-card w-full max-w-md border border-sipar-border p-5">
        <h3 className="text-lg font-semibold">{title}</h3>
        <p className="mt-2 text-sm text-sipar-muted">{description}</p>
        <div className="mt-5 flex justify-end gap-2">
          <button className="btn-secondary" onClick={onCancel}>
            Cancelar
          </button>
          <button className="btn-danger" onClick={onConfirm}>
            {confirmText || 'Confirmar'}
          </button>
        </div>
      </div>
    </div>
  )
}
