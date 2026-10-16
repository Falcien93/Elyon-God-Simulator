/** Story, dialogue, codex, and tool definitions. */

export const DAYS = [
  {
    id: "light",
    numeral: "the first day",
    title: "Light",
    detail: "The deep is unformed. Speak light into it.",
    evening: "Evening came, and morning — the first day.",
  },
  {
    id: "waters",
    numeral: "the second day",
    title: "Waters",
    detail: "Divide the waters. Let a sea, a river, and a lake take their places.",
    evening: "Evening came, and morning — the second day.",
  },
  {
    id: "land",
    numeral: "the third day",
    title: "Dry land",
    detail: "Call the dry land up out of the dark, and let a garden floor appear.",
    evening: "Evening came, and morning — the third day.",
  },
  {
    id: "grove",
    numeral: "the third day",
    title: "Seed",
    detail: "Bring forth grass and trees. Set the Tree of Life and the Tree of Knowledge in the midst.",
    evening: "The ground answered. Fruit took its color.",
  },
  {
    id: "lights",
    numeral: "the fourth day",
    title: "Luminaries",
    detail: "Set a greater light and a lesser light, so the garden can tell its hours.",
    evening: "Evening came, and morning — the fourth day.",
  },
  {
    id: "creatures",
    numeral: "the fifth and sixth days",
    title: "Living creatures",
    detail: "Fill the water, the air, and the grass with living things.",
    evening: "The garden began to move of its own accord.",
  },
  {
    id: "humanity",
    numeral: "the sixth day",
    title: "Humanity",
    detail: "Form a man, speak with him, and then form his companion.",
    evening: "Two breaths moved in the garden, and neither was alone.",
  },
  {
    id: "rest",
    numeral: "the seventh day",
    title: "Rest",
    detail: "Descend and draw near to each of them beneath the trees.",
    evening: "You rested, and the work did not unwind.",
  },
];

export const SHAPES = {
  water: { label: "Water", cost: 6, hint: "1" },
  meadow: { label: "Meadow", cost: 4, hint: "2" },
  bloom: { label: "Bloom", cost: 3, hint: "3" },
  tree: { label: "Tree", cost: 8, hint: "4" },
  beast: { label: "Beast", cost: 10, hint: "5" },
  fish: { label: "Fish", cost: 8, hint: "6" },
  bird: { label: "Bird", cost: 8, hint: "7" },
  bless: { label: "Bless", cost: 8, hint: "8" },
};

export const BEAST_CYCLE = ["deer", "sheep", "lion"];

export const CODEX = {
  light: {
    title: "Light",
    body: "Light is not a lamp. It is how anything becomes visible to anything else, including you.",
  },
  waters: {
    title: "Waters",
    body: "The sea holds the edge of the garden. The river is a road that does not choose its walkers. The lake keeps the sky.",
  },
  land: {
    title: "Dry land",
    body: "Soil is a promise that weight will be answered. Grass is that promise kept softly.",
  },
  grove: {
    title: "The two trees",
    body: "The Tree of Life sweetens what is already good. The Tree of Knowledge ripens a difference: before and after.",
  },
  lights: {
    title: "Hours",
    body: "A world without hours cannot tell rest from labor. The sun and the moon are how the garden remembers itself.",
  },
  creatures: {
    title: "Creatures",
    body: "They are not ornaments. Each one wants, flees, or follows. Naming them does not make them yours. It lets them answer.",
  },
  adam: {
    title: "Adam",
    body: "The first speaker besides yourself. He learns the garden by walking it, and learns you by how you answer loneliness.",
  },
  eve: {
    title: "Eve",
    body: "Not a copy. A second way of being awake. She looks at the tree longer than he does, because wonder and appetite share a root.",
  },
  names: {
    title: "Names",
    body: "A name is a small commandment the creature can survive. Speak it, and the garden becomes a household.",
  },
  word: {
    title: "The word",
    body: "A commandment draws a line. Silence draws a different line. Both are acts. Neither can be unspoken later.",
  },
  choice: {
    title: "The choice",
    body: "You may keep them, release them, or close the question by force. The garden will remember which.",
  },
};

const close = { label: "Leave them in peace", goto: "close" };

/** @type {Record<string, object>} */
export const NODES = {
  adam_first: {
    id: "adam_first",
    speaker: "adam",
    lines: [
      "There is a voice, and there is weight, and I am between them.",
      "I was not. Now the air is inside me. Are you the one who pushed it there?",
    ],
    choices: [
      { label: "You are Adam.", goto: "adam_awake", fx: ["name:adam:Adam", "flag:adam_named", "codex:adam", "trust:adam:8"] },
      { label: "Choose the name yourself — tell me what to call you.", goto: "adam_name_input" },
    ],
  },
  adam_name_input: {
    id: "adam_name_input",
    speaker: "adam",
    lines: ["Then set a sound upon me. I will answer to it."],
    input: { save: "adam", placeholder: "Adam", max: 16 },
    then: "adam_awake",
    fx: ["flag:adam_named", "codex:adam", "trust:adam:6", "wonder:adam:6"],
  },
  adam_awake: {
    id: "adam_awake",
    speaker: "adam",
    lines: [
      "{adam}. When I say it, I stay.",
      "The garden is louder than I am. Color, water, leaf. I can point, but I cannot call most of it.",
      "There is a place at my side where the light falls and no one stands. It is the only cold I feel.",
    ],
    onEnter: ["flag:adam_asked_companion"],
    choices: [
      { label: "You will not be left with that cold.", goto: "adam_hope", fx: ["trust:adam:6"] },
      { label: "Walk, and we will give the creatures names.", goto: "adam_name_start", fx: ["wonder:adam:4"] },
      close,
    ],
  },
  adam_hope: {
    id: "adam_hope",
    speaker: "adam",
    lines: ["If another breath comes, let them be awake as I am awake. I do not want an echo. I want a voice that can refuse me."],
    choices: [{ label: "So it will be.", goto: "close", fx: ["trust:adam:4"] }, { label: "First, the creatures.", goto: "adam_name_start" }],
  },
  adam_hub_unnamed: {
    id: "adam_hub_unnamed",
    speaker: "adam",
    lines: ["I am here. The unnamed things keep looking up, as if a word were late."],
    choices: [
      { label: "Let us name them.", goto: "adam_name_start" },
      { label: "How is the garden?", goto: "adam_topic_early" },
      { label: "What do you fear?", goto: "adam_topic_fear" },
      close,
    ],
  },
  adam_hub: {
    id: "adam_hub",
    speaker: "adam",
    lines: ["The names hold. Tell me what you came down to say."],
    choices: [
      { label: "How is the garden?", goto: "adam_topic_garden" },
      { label: "Speak of {eve}.", goto: "adam_topic_eve", when: "eve" },
      { label: "The two trees.", goto: "adam_topic_trees" },
      { label: "The word you spoke.", goto: "adam_topic_word", when: "commandment" },
      { label: "The silence you kept.", goto: "adam_topic_silence", when: "silence" },
      close,
    ],
  },
  adam_waiting_eve: {
    id: "adam_waiting_eve",
    speaker: "adam",
    lines: ["I keep a place beside me. The grass there is not worn, because only I have walked."],
    choices: [
      { label: "Soon.", goto: "close", fx: ["trust:adam:2"] },
      { label: "Name the creatures while you wait.", goto: "adam_name_start" },
    ],
  },
  adam_waiting_named: {
    id: "adam_waiting_named",
    speaker: "adam",
    lines: ["The creatures answer when I call. The place beside me still does not."],
    choices: [
      { label: "Soon.", goto: "close", fx: ["trust:adam:2"] },
      close,
    ],
  },
  adam_name_start: {
    id: "adam_name_start",
    speaker: "adam",
    lines: ["They come nearer when you are near. I think they are waiting for a sound that means them and not the grass."],
    next: "adam_name_deer",
  },
  adam_name_deer: {
    id: "adam_name_deer",
    speaker: "adam",
    lines: ["This one carries a quiet crown of horn, and it startles at its own grace."],
    choices: [
      { label: "Call them Hart.", goto: "adam_name_sheep", fx: ["namekind:deer:Hart"] },
      { label: "Call them Deer.", goto: "adam_name_sheep", fx: ["namekind:deer:Deer"] },
      { label: "I will choose another name.", goto: "adam_name_deer_input" },
    ],
  },
  adam_name_deer_input: {
    id: "adam_name_deer_input",
    speaker: "adam",
    lines: ["What shall the horned ones answer to?"],
    input: { save: "deer", placeholder: "Hart", max: 16 },
    then: "adam_name_sheep",
  },
  adam_name_sheep: {
    id: "adam_name_sheep",
    speaker: "adam",
    lines: ["These stay close. Their fear is small, and their eyes are older than their legs."],
    choices: [
      { label: "Call them Flock.", goto: "adam_name_lion", fx: ["namekind:sheep:Flock"] },
      { label: "Call them Lamb.", goto: "adam_name_lion", fx: ["namekind:sheep:Lamb"] },
      { label: "Another name.", goto: "adam_name_sheep_input" },
    ],
  },
  adam_name_sheep_input: {
    id: "adam_name_sheep_input",
    speaker: "adam",
    lines: ["Name the soft ones."],
    input: { save: "sheep", placeholder: "Flock", max: 16 },
    then: "adam_name_lion",
  },
  adam_name_lion: {
    id: "adam_name_lion",
    speaker: "adam",
    lines: ["This one does not come close. The grass changes where it has been. I am not its master. I would still like to call it something that is not a warning."],
    choices: [
      { label: "Call them Lion.", goto: "adam_named_done", fx: ["namekind:lion:Lion"] },
      { label: "Call them Sun-mane.", goto: "adam_named_done", fx: ["namekind:lion:Sun-mane"] },
      { label: "Another name.", goto: "adam_name_lion_input" },
    ],
  },
  adam_name_lion_input: {
    id: "adam_name_lion_input",
    speaker: "adam",
    lines: ["What do you call the one that does not kneel?"],
    input: { save: "lion", placeholder: "Lion", max: 16 },
    then: "adam_named_done",
  },
  adam_named_done: {
    id: "adam_named_done",
    speaker: "adam",
    lines: [
      "When I speak the names, heads turn. That is a strange power. It does not feel like ownership.",
      "Thank you for not naming them only for me.",
    ],
    onEnter: ["flag:beasts_named", "codex:names", "wonder:adam:8", "trust:adam:6"],
    choices: [close],
  },
  adam_topic_early: {
    id: "adam_topic_early",
    speaker: "adam",
    lines: ["The ground holds me. I did not know weight could be a kindness."],
    choices: [{ label: "Back", goto: "adam_hub_unnamed" }],
  },
  adam_topic_garden: {
    id: "adam_topic_garden",
    speaker: "adam",
    lines: ["The river works whether I watch it or not. That comforts me. I do not have to hold the world up with attention."],
    choices: [{ label: "Back", goto: "adam_hub" }],
  },
  adam_topic_eve: {
    id: "adam_topic_eve",
    speaker: "adam",
    lines: ["{eve} sees the edges of things. I see the middles. Between us the garden is almost fully looked at."],
    choices: [{ label: "Back", goto: "adam_hub" }],
  },
  adam_topic_trees: {
    id: "adam_topic_trees",
    speaker: "adam",
    lines: [
      "One tree smells like rest. I could live beside it and forget to count days.",
      "The other smells like a question. {eve} stands nearer to that one. I pretend not to count her steps.",
    ],
    choices: [{ label: "Back", goto: "adam_hub" }],
  },
  adam_topic_word: {
    id: "adam_topic_word",
    speaker: "adam",
    lines: ["Your word was: “{commandment}”. I repeat it when the fruit is bright, so my mouth is already full of something else."],
    choices: [{ label: "Back", goto: "adam_hub" }],
  },
  adam_topic_silence: {
    id: "adam_topic_silence",
    speaker: "adam",
    lines: ["You gave no prohibition. I keep waiting for one, the way a path waits for a fence. {eve} says waiting is its own answer."],
    choices: [{ label: "Back", goto: "adam_hub" }],
  },
  adam_return: {
    id: "adam_return",
    speaker: "adam",
    lines: ["I am still listening."],
    choices: [
      { label: "The garden", goto: "adam_topic_garden" },
      { label: "{eve}", goto: "adam_topic_eve" },
      { label: "The trees", goto: "adam_topic_trees" },
      { label: "Your word", goto: "adam_topic_word" },
      close,
    ],
  },
  adam_topic_fear: {
    id: "adam_topic_fear",
    speaker: "adam",
    lines: ["I fear a garden in which every voice is mine. Even yours, if it never allowed another."],
    choices: [{ label: "Back", goto: "adam_hub_unnamed" }],
  },
  eve_first: {
    id: "eve_first",
    speaker: "eve",
    lines: [
      "I came up already looking. That seems to be my way.",
      "He was there, and you were there, and the fruit was already red. Nobody had to explain hunger. Only whether to obey it.",
    ],
    onEnter: ["flag:eve_greeted", "codex:eve", "trust:eve:8", "wonder:eve:8"],
    choices: [
      { label: "What do you see?", goto: "eve_sees" },
      { label: "Adam is glad of you.", goto: "eve_adam", fx: ["trust:eve:4"] },
      close,
    ],
  },
  eve_sees: {
    id: "eve_sees",
    speaker: "eve",
    lines: ["I see that the garden is finished and unfinished at the same time. You left a tree that is a door. Doors are a kind of trust."],
    choices: [{ label: "Remember that.", goto: "close", fx: ["wonder:eve:4"] }],
  },
  eve_adam: {
    id: "eve_adam",
    speaker: "eve",
    lines: ["He learns me without trying to finish me. I love him for the unfinished part."],
    choices: [close],
  },
  eve_hub: {
    id: "eve_hub",
    speaker: "eve",
    lines: ["You came down. The light changes when you do. Speak."],
    choices: [
      { label: "What are you thinking of?", goto: "eve_think" },
      { label: "And Adam?", goto: "eve_adam" },
      { label: "The Tree of Knowledge.", goto: "eve_tree" },
      close,
    ],
  },
  eve_think: {
    id: "eve_think",
    speaker: "eve",
    lines: ["Whether a gift that cannot be refused is still a gift. I think it is. I also think the other kind matters more."],
    choices: [{ label: "Back", goto: "eve_hub" }],
  },
  eve_tree: {
    id: "eve_tree",
    speaker: "eve",
    lines: ["It is beautiful in a way that makes my teeth ache. I have not taken it. I want you to know the difference between not taking and not wanting."],
    choices: [{ label: "I know the difference.", goto: "close", fx: ["trust:eve:5", "will:eve:4"] }],
  },
  eve_choice: {
    id: "eve_choice",
    speaker: "eve",
    lines: [
      "Something low spoke from the branches. It knew my name, or it knew how names work.",
      "It said the fruit is how a creature stops being only loved and starts being responsible.",
      "I have not eaten. I wanted you to be here when I decided whether that voice was only hunger wearing cleverness.",
    ],
    choices: [
      {
        label: "Leave the fruit. I am with you either way, and I ask you to trust me.",
        goto: "eve_harmony",
        fx: ["ending:harmony", "trust:eve:10", "order:14", "wonder:-4"],
      },
      {
        label: "I will not choose for you.",
        goto: "eve_hands",
        fx: ["ending:hands", "will:eve:12"],
      },
      {
        label: "Then I will put the fruit out of reach.",
        goto: "eve_order",
        fx: ["ending:order", "flag:tree_guarded", "flag:serpent_gone", "order:18", "wonder:-16"],
      },
    ],
  },
  eve_harmony: {
    id: "eve_harmony",
    speaker: "eve",
    lines: [
      "Then I leave it. Not because the color faded. Because you asked as one who stays, not as a lock.",
      "If wonder ever needs a door again, we will ask you to the threshold before we touch it.",
    ],
    choices: [close],
  },
  eve_hands: {
    id: "eve_hands",
    speaker: "eve",
    lines: ["Then watch. I will not pretend this bite is an accident."],
    choices: [close],
  },
  eve_order: {
    id: "eve_order",
    speaker: "eve",
    lines: ["Then the question is closed, and I am safe, and I am smaller. I will love you without the door. I will know what it cost."],
    choices: [close],
  },
  serpent_meet: {
    id: "serpent_meet",
    speaker: "serpent",
    lines: [
      "You came yourself. Good. I dislike speaking only to the hungry.",
      "I do not tell them you are false. I tell them the fruit is ripe. Those are different sentences. They hate that I am difficult to answer.",
    ],
    choices: [
      {
        label: "Be gone from this garden.",
        goto: "serpent_gone",
        fx: ["ending:order", "flag:serpent_gone", "flag:tree_guarded", "order:16", "wonder:-14"],
      },
      { label: "Why do you care what they choose?", goto: "serpent_why" },
      { label: "I will not bandy words with you.", goto: "close", fx: ["wonder:4"] },
    ],
  },
  serpent_why: {
    id: "serpent_why",
    speaker: "serpent",
    lines: [
      "Because a garden without a real refusal is a picture of a garden.",
      "I am not their friend. I am the question you planted when you planted that tree. You may strike the question. The scar will still be shaped like it.",
    ],
    choices: [
      {
        label: "Be gone.",
        goto: "serpent_gone",
        fx: ["ending:order", "flag:serpent_gone", "flag:tree_guarded", "order:16", "wonder:-14"],
      },
      { label: "They will answer for themselves.", goto: "close", fx: ["will:eve:6", "wonder:6"] },
    ],
  },
  serpent_gone: {
    id: "serpent_gone",
    speaker: "serpent",
    lines: ["Then I go. The brightness will be very well behaved."],
    choices: [close],
  },
  adam_epilogue_harmony: {
    id: "adam_epilogue_harmony",
    speaker: "adam",
    lines: ["We left the fruit. The tree is still a question, but it is not an emergency. I sleep. That is new."],
    choices: [close],
  },
  eve_epilogue_harmony: {
    id: "eve_epilogue_harmony",
    speaker: "eve",
    lines: ["I still look at it. Looking is not the same as reaching. You trusted me with the difference, so I am keeping it."],
    choices: [close],
  },
  adam_epilogue_exile: {
    id: "adam_epilogue_exile",
    speaker: "adam",
    lines: [
      "We ate. The garden did not become ugly. We became unable to stand in it as we were.",
      "You clothed us anyway. If the east is where we must walk, walk near us until the gate, even if you cannot stay beyond it.",
    ],
    choices: [close],
  },
  eve_epilogue_exile: {
    id: "eve_epilogue_exile",
    speaker: "eve",
    lines: ["I wanted knowing, and knowing came with a draft. I am not sorry I was brave. I am sorry the bravery had a price you also pay."],
    choices: [close],
  },
  adam_epilogue_wonder: {
    id: "adam_epilogue_wonder",
    speaker: "adam",
    lines: ["There was no law to break, so the bite did not cast us out. It only made us more awake. The garden feels larger. I hold {eve}'s hand so I do not get lost in it."],
    choices: [close],
  },
  eve_epilogue_wonder: {
    id: "eve_epilogue_wonder",
    speaker: "eve",
    lines: ["You did not forbid, and you did not rescue me from my own hand. I think that is the most frightening kindness. We are still here. I am still looking."],
    choices: [close],
  },
  adam_epilogue_order: {
    id: "adam_epilogue_order",
    speaker: "adam",
    lines: ["The danger is gone. I should be only grateful. I am grateful, and I am also looking for a weight that used to be here."],
    choices: [close],
  },
  eve_epilogue_order: {
    id: "eve_epilogue_order",
    speaker: "eve",
    lines: ["You closed the door to keep us. I stayed. Love can live in a safe room. It paces."],
    choices: [close],
  },
};

export const ENDINGS = {
  harmony: {
    id: "harmony",
    title: "The garden kept",
    paragraphs: [
      "They left the fruit on the branch. Not from dullness — Eve could still describe its color better than any praise you had spoken. They left it because you asked, and because you stayed beside the asking.",
      "The serpent’s voice dried up like a creek in a careful summer. Order deepened. Wonder did not die; it narrowed into loyalty, which is a kind of sight. You walked the garden in the evening and the work did not unwind.",
    ],
  },
  exile: {
    id: "exile",
    title: "East of the garden",
    paragraphs: [
      "They ate, and knowing entered like weather. They did not become monsters. They became people who could not pretend the bite was someone else’s hand. Shame arrived, and so did skill.",
      "You did not strike them. You clothed them, and you walked them toward the eastern grass where the river loosens into the wild. The garden remained behind them, beautiful and no longer simple. Love went with them past the gate.",
    ],
  },
  wonder: {
    id: "wonder",
    title: "The open orchard",
    paragraphs: [
      "You never drew the line. When they tasted the fruit, no law broke, because no law had been set. The bite did not exile them. It changed the grain of their seeing. Colors took on insides.",
      "Some gardens are kept by fences and some by company. This one stayed, stranger and kinder, with you still able to descend. They were not innocent. They were uncondemned. The difference filled the evening like a second light.",
    ],
  },
  order: {
    id: "order",
    title: "The closed question",
    paragraphs: [
      "You ended the trial. The low voice was driven out, and the fruit was put beyond desire — guarded, darkened, no longer a door. Nothing in the garden could fall. The evenings were very peaceful.",
      "Adam slept easily. Eve loved you without rebellion and without the particular brightness rebellion makes room for. Order shone like polished stone. When you walked among the trees, one shape of wonder was missing, and you knew its name.",
    ],
  },
};
