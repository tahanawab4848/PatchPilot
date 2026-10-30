import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-gradient-to-r from-accent to-[#15a8be] text-[#0b0f17] font-semibold shadow-glow-sm hover:shadow-glow-md hover:brightness-110",
        destructive:
          "bg-status-error/90 text-white font-medium hover:bg-status-error shadow-sm hover:shadow-[0_0_15px_-3px_rgba(248,113,113,0.3)]",
        outline:
          "border border-border/80 bg-surface-1/60 backdrop-blur-xs text-text-primary hover:bg-surface-2 hover:border-accent/40 shadow-xs",
        secondary:
          "bg-surface-2/90 border border-border/50 text-text-primary hover:bg-surface-3 hover:text-white shadow-xs",
        ghost:
          "text-text-secondary hover:text-text-primary hover:bg-surface-2/70",
        link: "text-text-link underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-7 px-3 text-xs",
        lg: "h-11 px-6 text-base",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
