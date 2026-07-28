"use client"

import { useToast } from "@/hooks/use-toast"
import {
  Toast,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
} from "@/components/ui/toast"

const AUTO_DISMISS_MS = 3000

export function Toaster() {
  const { toasts } = useToast()

  return (
    <ToastProvider duration={AUTO_DISMISS_MS} swipeDirection="up">
      {toasts.map(function ({ id, title, description, action, ...props }) {
        return (
          <Toast key={id} {...props}>
            <div className="grid gap-0 flex-1 min-w-0">
              {title && <ToastTitle className="truncate">{title}</ToastTitle>}
              {description && (
                <ToastDescription className="truncate">{description}</ToastDescription>
              )}
            </div>
            {action}
            <ToastClose />
          </Toast>
        )
      })}
      <ToastViewport />
    </ToastProvider>
  )
}
