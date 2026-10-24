// Imported by server routes/pages only. Answers are never sent with the question catalog.
export const lessons = [
  {
    id: "money",
    title: "From money to Bitcoin",
    topic: "Foundations",
    minutes: 4,
    objective:
      "Explain what cryptocurrency does without assuming its price will rise.",
    paragraphs: [
      "Money helps people exchange value, compare prices and save purchasing power. Digital money is a record of value handled electronically; it is not automatically cryptocurrency.",
      "Bitcoin uses a shared ledger and consensus rules to validate transfers without one central ledger operator. Its supply rules do not guarantee stable prices or future purchasing power.",
    ],
    example:
      "Think of a shared notebook whose updates must follow agreed rules. Owning a notebook entry does not guarantee someone will buy it at a higher price.",
  },
  {
    id: "wallets",
    title: "Wallets, keys & blockchain",
    topic: "Foundations",
    minutes: 4,
    objective: "Distinguish a wallet from the assets recorded on a blockchain.",
    paragraphs: [
      "A blockchain records ordered transactions under a network's rules. A wallet manages keys and helps create transactions; coins do not literally sit inside the wallet app.",
      "A private key authorizes spending. A recovery phrase can grant access to those keys. Never share it, paste it into support chats or store it in a trading journal. Transactions may be difficult or impossible to reverse.",
    ],
    example:
      "Your wallet is closer to a key ring than a bag of coins. Losing the keys can mean losing access; a screenshot of a balance cannot restore them.",
  },
  {
    id: "risk",
    title: "Risk & original R",
    topic: "Risk management",
    minutes: 5,
    objective: "Separate a planned price risk from a guaranteed maximum loss.",
    paragraphs: [
      "Planned price risk measures the loss between entry and the original stop at the original quantity. Actual losses can exceed that estimate because of gaps, slippage and costs.",
      "Realized R compares net realized PnL with original planned risk. Keep the original denominator after a partial exit. Missing original risk means R is unavailable, not zero.",
    ],
    example:
      "A synthetic trade with $20 original risk and $22 net profit returns 1.10R. It says nothing by itself about whether the next trade will win.",
  },
  {
    id: "leverage",
    title: "Leverage without illusions",
    topic: "Risk management",
    minutes: 4,
    objective:
      "Understand exposure, margin and liquidation as different concepts.",
    paragraphs: [
      "Leverage lets an account support more notional exposure than its posted margin. It does not multiply execution-price PnL a second time when quantity already describes the exposure.",
      "Estimated margin is not a broker's complete collateral or liquidation model. Maintenance margin, fees, funding, mark prices and cross-account positions can matter. A stop is not a guaranteed liquidation safeguard.",
    ],
    example:
      "For a hypothetical $1,000 notional position at 10× leverage, simple initial margin is $100. A 1% price move changes gross value by about $10 for a linear position, not $100.",
  },
  {
    id: "candles",
    title: "Read a candle",
    topic: "Market basics",
    minutes: 3,
    objective:
      "Read open, high, low and close without treating a candle as a prediction.",
    paragraphs: [
      "A candlestick summarizes open, highest, lowest and close prices during one interval. The body connects open to close; wicks show the extremes.",
      "A close above the open is commonly called bullish for that interval. Candle colors are chart settings, not universal rules. A bullish candle is a description, not evidence that the next price must rise.",
    ],
    example:
      "Open 100, high 110, low 95, close 104: the interval closed higher, even though a buyer at 109 lost value by the close.",
  },
  {
    id: "lots",
    title: "Lots, pips & metals",
    topic: "Forex & metals",
    minutes: 5,
    objective:
      "Use declared contract specifications rather than assuming every symbol is identical.",
    paragraphs: [
      "Lots measure contract quantity. Underlying exposure depends on both lots and the broker's recorded contract size. Pip and tick sizes describe price increments; neither is automatically a fixed cash value.",
      "Many forex teaching examples use a 0.0001 pip and JPY examples use 0.01, but broker specifications must be checked. Gold and silver contract sizes can differ across products and brokers.",
    ],
    example:
      "With a fictional contract of 100 ounces per lot, 0.10 lots represents 10 ounces. A $2 move gives $20 gross for a long linear position before costs.",
  },
  {
    id: "costs",
    title: "Gross, net & partial exits",
    topic: "Journal skills",
    minutes: 4,
    objective: "Count costs once and keep currencies explicit.",
    paragraphs: [
      "Gross PnL comes from closed execution quantities and price changes. Net PnL includes recognized commissions, swaps and other signed adjustments. Actual fill prices already reflect their execution spread; do not subtract that spread again.",
      "A partial exit realizes only its closed quantity. Under AVA's incurred-once policy, an entry commission is recognized once, not once per exit. Reporting-currency totals need explicit dated conversions.",
    ],
    example:
      "Gross profit $26 plus signed costs of −$4 gives $22 net. JPY profit cannot be added to USD profit without a conversion policy.",
  },
  {
    id: "psychology",
    title: "Build a review habit",
    topic: "Trading psychology",
    minutes: 4,
    objective:
      "Record observable behavior and avoid conclusions from tiny samples.",
    paragraphs: [
      "Record your setup, rationale, emotions and mistakes close to the event. A good decision can lose money and a poor decision can win; outcome alone is not decision quality.",
      "Review comparable records over enough observations. AVA Trading IQ uses evidence gates, but passing them is not proof of statistical significance or a profitable future edge.",
    ],
    example:
      "Instead of writing 'I am bad at trading', record 'I increased quantity after a loss without reviewing planned risk'. That is a behavior you can inspect and change.",
  },
] as const;

export const questions = [
  {
    id: "money-1",
    lesson: "money",
    prompt: "Which statement about cryptocurrency is accurate?",
    choices: [
      "It guarantees rising purchasing power",
      "It uses network rules to record and transfer value",
      "All digital bank balances are Bitcoin",
      "A fixed supply prevents losses",
    ],
    answer: 1,
    explanation:
      "Cryptocurrency networks use defined rules for records and transfers. Their design does not guarantee purchasing power or investment returns.",
  },
  {
    id: "money-2",
    lesson: "money",
    prompt: "Which is a normal function of money?",
    choices: [
      "Guaranteeing profit",
      "Removing all counterparty risk",
      "Providing a unit for comparing prices",
      "Predicting market direction",
    ],
    answer: 2,
    explanation:
      "A unit of account lets people compare prices. Money can also serve as a medium of exchange and store of value, with different risks.",
  },
  {
    id: "wallets-1",
    lesson: "wallets",
    prompt: "What does a wallet primarily manage?",
    choices: [
      "Keys and transaction interactions",
      "Guaranteed returns",
      "Only physical coins",
      "A copy of every user's private key",
    ],
    answer: 0,
    explanation:
      "Wallets manage keys and help interact with the network. Assets are represented by ledger records, not files of coins inside an app.",
  },
  {
    id: "wallets-2",
    lesson: "wallets",
    prompt:
      "A support agent asks for your recovery phrase. What should you do?",
    choices: [
      "Send half of it",
      "Post it in your journal",
      "Share it if they know your balance",
      "Keep it secret and reject the request",
    ],
    answer: 3,
    explanation:
      "A recovery phrase can grant control of assets. A legitimate balance inquiry does not require it. Keep it out of chats and journal attachments.",
  },
  {
    id: "risk-1",
    lesson: "risk",
    prompt:
      "Original planned risk is $20 and realized net profit is $22. What is realized R?",
    choices: ["0.91R", "1.10R", "22R", "2R"],
    answer: 1,
    explanation:
      "Realized R = net profit ÷ original planned risk = 22 ÷ 20 = 1.10R. Costs belong in the net result.",
  },
  {
    id: "risk-2",
    lesson: "risk",
    prompt:
      "After closing half a position, which risk denominator does AVA retain?",
    choices: [
      "Half the original risk",
      "The latest trailing-stop distance",
      "The original recorded planned risk",
      "The previous trade's loss",
    ],
    answer: 2,
    explanation:
      "Partial exits do not rewrite original planned risk. This keeps cumulative realized R comparable throughout the position's life.",
  },
  {
    id: "leverage-1",
    lesson: "leverage",
    prompt:
      "A linear position has $1,000 notional exposure. What is gross PnL for a favorable 1% move?",
    choices: ["About $10", "Always $100", "About $1,000", "It cannot lose"],
    answer: 0,
    explanation:
      "For the stated linear exposure, 1% of $1,000 is $10 before costs. Do not multiply by leverage again after exposure is already specified.",
  },
  {
    id: "leverage-2",
    lesson: "leverage",
    prompt:
      "Does a simple notional/leverage margin estimate determine exact liquidation?",
    choices: [
      "Yes, for every broker",
      "Yes, if the stop is entered",
      "Only when the candle is green",
      "No; broker margin rules and other factors matter",
    ],
    answer: 3,
    explanation:
      "Liquidation depends on the broker/product's margin rules and account conditions. An educational initial-margin estimate is not a liquidation model.",
  },
  {
    id: "candles-1",
    lesson: "candles",
    prompt: "A candle opens at 100 and closes at 104. What can you conclude?",
    choices: [
      "The next candle must rise",
      "It closed above its open",
      "Every buyer made money",
      "Its low was 100",
    ],
    answer: 1,
    explanation:
      "Only the open-to-close direction follows from those two numbers. The next interval, intraperiod low and each trader's outcome are unknown.",
  },
  {
    id: "candles-2",
    lesson: "candles",
    prompt: "What do a candle's wicks normally represent?",
    choices: [
      "Guaranteed support levels",
      "Fees and funding",
      "Interval price extremes",
      "Future buy orders",
    ],
    answer: 2,
    explanation:
      "Wicks show the recorded high and low for the interval. They do not reveal future orders or guaranteed support/resistance.",
  },
  {
    id: "lots-1",
    lesson: "lots",
    prompt:
      "A fictional gold contract is 100 ounces per lot. How much is 0.10 lots?",
    choices: ["10 ounces", "100 ounces", "1 ounce", "The same for all brokers"],
    answer: 0,
    explanation:
      "0.10 × 100 = 10 ounces under this explicitly stated specification. Actual broker contract sizes must be verified.",
  },
  {
    id: "lots-2",
    lesson: "lots",
    prompt: "Can one pip always be treated as the same cash value?",
    choices: [
      "Yes, always $10",
      "Yes, for every JPY pair",
      "Yes, regardless of quantity",
      "No; contract, quantity and currencies matter",
    ],
    answer: 3,
    explanation:
      "Pip size is a price increment. Cash value depends on exposure and currency conversion. Tick and pip sizes are not interchangeable.",
  },
  {
    id: "costs-1",
    lesson: "costs",
    prompt:
      "Gross profit is $26 and signed adjustments total −$4. What is net profit?",
    choices: ["$30", "$22", "$26", "$4"],
    answer: 1,
    explanation:
      "Net = gross + signed adjustments = 26 + (−4) = $22. A charge is negative and a credit positive in the CFD adjustment contract.",
  },
  {
    id: "costs-2",
    lesson: "costs",
    prompt:
      "Should the same entry commission be deducted again after every partial exit?",
    choices: [
      "Yes, to be conservative",
      "Only after a winning exit",
      "No, it is recognized once under incurred_once",
      "Only for forex",
    ],
    answer: 2,
    explanation:
      "Counting the same charge more than once understates net performance. Each adjustment has a stable identity and occurrence time.",
  },
  {
    id: "psychology-1",
    lesson: "psychology",
    prompt: "Which journal note is most actionable?",
    choices: [
      "I doubled quantity after a loss without checking planned risk",
      "The market hates me",
      "I always lose",
      "This setup cannot fail",
    ],
    answer: 0,
    explanation:
      "An observable behavior can be checked against records and changed. Absolute judgments and guaranteed-outcome claims are not useful evidence.",
  },
  {
    id: "psychology-2",
    lesson: "psychology",
    prompt: "Does a high win rate from a few trades establish a reliable edge?",
    choices: [
      "Yes, if above 80%",
      "Yes, without costs",
      "Yes, for a popular setup",
      "No; sample, risk, costs and uncertainty matter",
    ],
    answer: 3,
    explanation:
      "Win rate omits payoff size, costs, selection and uncertainty. Passing a product's evidence threshold still does not prove predictive significance.",
  },
] as const;

export function publicLearning() {
  return {
    lessons,
    questions: questions.map(({ id, lesson, prompt, choices }) => ({
      id,
      lesson,
      prompt,
      choices,
    })),
  };
}
