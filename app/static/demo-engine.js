// Состояние учебного примера хранится только в открытой вкладке.
globalThis.RemiDemoEngine = {
  start(questions) {
    if (!Array.isArray(questions) || questions.length === 0) throw new Error('Нет вопросов');
    return { questions, index: 0, checked: false, finished: false, chosen: null };
  },
  answer(state, option) {
    if (state.finished || state.checked || !Number.isInteger(option) || option < 0 || option >= state.questions[state.index].options.length) {
      throw new Error('Некорректный ответ');
    }
    return { ...state, checked: true, chosen: option };
  },
  next(state) {
    if (!state.checked || state.finished) throw new Error('Сначала проверьте ответ');
    if (state.index + 1 >= state.questions.length) return { ...state, finished: true };
    return { ...state, index: state.index + 1, checked: false, chosen: null };
  },
};

if (typeof module !== 'undefined') module.exports = globalThis.RemiDemoEngine;
