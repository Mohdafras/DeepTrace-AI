import { useEffect, useId, useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';

/** Native modal dialogs provide focus containment, Escape dismissal and an inert background. */
export function Dialog({ title, onClose, children, wide = false, drawer = false }: {
  title: string; onClose: () => void; children: ReactNode; wide?: boolean; drawer?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const dialog = ref.current;
    const oldOverflow = document.body.style.overflow;
    dialog?.showModal();
    document.body.style.overflow = 'hidden';
    return () => {
      dialog?.close();
      document.body.style.overflow = oldOverflow;
      if (previous?.isConnected) previous.focus();
    };
  }, []);
  return <dialog ref={ref} aria-labelledby={titleId} className={`app-dialog ${wide ? 'dialog-wide' : ''} ${drawer ? 'dialog-drawer' : ''}`}
    onCancel={event => { event.preventDefault(); onClose(); }}
    onClick={event => { if (event.target === event.currentTarget) { const bounds = event.currentTarget.getBoundingClientRect(); if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) onClose(); } }}>
    <div className="flex items-center justify-between gap-3 border-b border-[#243247] pb-4 mb-4">
      <h2 id={titleId} className="text-base font-bold text-[#F8FAFC]">{title}</h2>
      <button type="button" onClick={onClose} aria-label={`Close ${title}`} className="p-2 rounded-lg text-[#94A3B8] hover:bg-[#243247] hover:text-white shrink-0"><X size={18} /></button>
    </div>
    {children}
  </dialog>;
}
