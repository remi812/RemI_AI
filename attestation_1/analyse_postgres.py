from pathlib import Path
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parent
df = pd.read_csv(root / 'postgres_export.csv')
required = ['session_id', 'initial_equations_count', 'initial_equations_correct',
            'initial_derivatives_count', 'initial_derivatives_correct',
            'followup_count', 'followup_correct', 'needs_review']
missing = df[required].isna().sum()
valid = (df[required].notna().all(axis=1) & df.initial_equations_count.eq(2)
         & df.initial_derivatives_count.eq(2) & df.followup_count.eq(3)
         & df.initial_equations_correct.between(0,2)
         & df.initial_derivatives_correct.between(0,2)
         & df.followup_correct.between(0,3) & df.needs_review.isin([0,1]))
duplicates = int(df.duplicated('session_id').sum())
clean = df.loc[valid].drop_duplicates('session_id').copy()
clean.to_csv(root / 'cleaned.csv', index=False, encoding='utf-8-sig')
charts = root / 'charts'
charts.mkdir(exist_ok=True)

def plot(column, title, xlabel, filename):
    groups = clean.groupby(column)['needs_review'].agg(['sum','count']).sort_index()
    plt.figure(figsize=(7.4,4.2))
    xs = list(range(len(groups)))
    plt.bar(xs, groups['sum']/groups['count']*100, color='#486981')
    plt.xticks(xs, groups.index)
    plt.ylim(0,100)
    plt.ylabel('Доля с затруднением, %')
    plt.xlabel(xlabel)
    plt.title(title)
    for i, (_, row) in enumerate(groups.iterrows()):
        plt.text(i, row['sum']/row['count']*100+2, f"{int(row['sum'])}/{int(row['count'])}", ha='center')
    plt.tight_layout()
    plt.savefig(charts / filename, dpi=160)
    plt.close()
    return {str(int(k)): {'count':int(v['count']), 'review':int(v['sum'])} for k,v in groups.iterrows()}

deriv = plot('initial_derivatives_correct','Первые ответы по производным и дополнительная проверка','Правильных ответов из двух','derivatives.png')
equat = plot('initial_equations_correct','Первые ответы по уравнениям и дополнительная проверка','Правильных ответов из двух','equations.png')
stats = {'sessions':len(df), 'answers':{'initial':int((df.initial_equations_count+df.initial_derivatives_count).sum()), 'followup':int(df.followup_count.sum())},
         'missing':{k:int(v) for k,v in missing.items()}, 'invalid':int((~valid).sum()),
         'duplicate':duplicates, 'clean':len(clean), 'target_positive':int(clean.needs_review.sum()),
         'by_derivatives':deriv, 'by_equations':equat}
(root / 'results.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
print('Строк:',len(df),'после проверки:',len(clean),'пропусков:',int(missing.sum()))
