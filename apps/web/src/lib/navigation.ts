import {
  LayoutDashboard,
  BookOpen,
  Radar,
  FlaskConical,
  GraduationCap,
  Swords,
  WalletCards,
} from "lucide-react";
export const navigation = [
  {
    href: "/",
    label: "Command Center",
    icon: LayoutDashboard,
    phase: 1,
    description: "Your performance, research and learning at a glance.",
  },
  {
    href: "/journal",
    label: "Trading Journal",
    icon: BookOpen,
    phase: 2,
    description: "Build a clearer picture of your trading decisions.",
  },
  {
    href: "/accounts",
    label: "Trading Accounts",
    icon: WalletCards,
    phase: 2,
    description: "Practice accounts and documented instrument specifications.",
  },
  {
    href: "/markets",
    label: "Market Screener",
    icon: Radar,
    phase: 3,
    description: "Explore assets with transparent market observations.",
  },
  {
    href: "/lab",
    label: "Mechanics Lab",
    icon: FlaskConical,
    phase: 3,
    description: "Understand market mechanics through safe simulations.",
  },
  {
    href: "/academy",
    label: "Crypto Academy",
    icon: GraduationCap,
    phase: 4,
    description:
      "A guided path from first principles to quantitative research.",
  },
  {
    href: "/trivia",
    label: "Trivia Arena",
    icon: Swords,
    phase: 5,
    description:
      "Turn knowledge into a habit with challenges and learning games.",
  },
];
