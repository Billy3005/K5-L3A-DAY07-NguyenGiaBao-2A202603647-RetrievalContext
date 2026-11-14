# Chấm mù (học viên) — không xem nhãn LLM trước khi điền

Cấu hình `agent_hrr_B_1shot`, split `test`, 15 câu. Với mỗi câu: đọc câu trả lời, đọc toàn văn chunk được trích, rồi điền vào `results/agent/blind_review.csv`:
- `student_grade`: 0/1/2 cho câu có đáp án (từ chối câu có đáp án = 0); để trống cho câu thiếu evidence
- `student_abstention_ok`: yes/no cho câu thiếu evidence
- `student_citations_ok`: số citation hỗ trợ đúng câu được gắn (ví dụ 2/2)
Sau đó chạy `python -m src.blind_review score`. **Không mở `labels/` hay `grading_spec_test.json` trước khi điền xong.**
Lưu ý: ['t01', 't05', 't10', 't11', 'ut1'] đã xuất hiện kèm nhãn LLM trong REVIEW.md, nên script báo đồng thuận riêng cho các câu còn lại (thật sự mù).

## t01 (direct)
**Câu hỏi:** When good weather boosted the supply of California salmon, what happened to the equilibrium price and quantity?

**Đáp án chuẩn / hành vi mong đợi:** The equilibrium price fell from $3.25 to $2.50 per pound and the equilibrium quantity rose from 250,000 to 550,000 salmon.

**Agent (answered):** Good weather increased the supply of California commercial salmon, shifting the supply curve to the right. The equilibrium price fell from $3.25 to $2.50 per pound, while the equilibrium quantity rose from 250,000 to 550,000 salmon [micro3e-p0078-pb1000-001] [micro3e-p0078-pb1000-000].

> **[micro3e-p0078-pb1000-001]** (trang 78)
>
> In short, good weather conditions increased supply of the California commercial salmon. The result was a higher equilibrium quantity of salmon bought and sold in the market at a lower price.

> **[micro3e-p0078-pb1000-000]** (trang 78)
>
> price is $3.25 per pound and the original equilibrium quantity is 250,000 fish. (This price per pound is what commercial buyers pay at the fishing docks. What consumers pay at the grocery is higher.)
> 
> Step 2. Did the economic event affect supply or demand? Good weather is an example of a natural condition that affects supply.
> 
> Step 3. Was the effect on supply an increase or a decrease? Good weather is a change in natural conditions that increases the quantity supplied at any given price. The supply curve shifts to the right, moving from the original supply curve S0 to the new supply curve S1, which Figure 3.16 and Table 3.6 show.
> 
> Step 4. Compare the new equilibrium price and quantity to the original equilibrium. At the new equilibrium E1, the equilibrium price falls from $3.25 to $2.50, but the equilibrium quantity increases from 250,000 to 550,000 salmon. Notice that the equilibrium quantity demanded increased, even though the demand curve did not move.

## t02 (paraphrase)
**Câu hỏi:** How does a job that demands many years of schooling affect how many workers are available for it, and what examples does the book give?

**Đáp án chuẩn / hành vi mong đợi:** The more required education, the lower the labor supply; e.g., fewer PhD mathematicians than high school math teachers, fewer cardiologists than primary care physicians, fewer physicians than nurses.

**Agent (answered):** The more education a job requires, the lower the supply of workers for it. The book's examples: there is a lower supply of PhD mathematicians than of high school mathematics teachers, a lower supply of cardiologists than of primary care physicians, and a lower supply of physicians than of nurses [micro3e-p0102-pb1000-001]. Similarly, tougher academic, certificate, or licensing qualifications reduce the number of qualified workers at any given wage [micro3e-p0102-pb1000-002].

> **[micro3e-p0102-pb1000-001]** (trang 102)
>
> An increased number of workers will cause the supply curve to shift to the right. An increased number of workers can be due to several factors, such as immigration, increasing population, an aging population, and changing demographics. Policies that encourage immigration will increase the supply of labor, and vice versa. Population grows when birth rates exceed death rates. This eventually increases supply of labor when the former reach working age. Another example of changing demographics is more women working outside of the home, which increases the supply of labor.
> 
> Required Education
> 
> The more required education, the lower the supply. There is a lower supply of PhD mathematicians than of high school mathematics teachers; there is a lower supply of cardiologists than of primary care physicians; and there is a lower supply of physicians than of nurses.
> 
> Government Policies

> **[micro3e-p0102-pb1000-002]** (trang 102)
>
> Government policies can also affect the supply of labor for jobs. Alternatively, the government may support rules that set high qualifications for certain jobs: academic training, certificates or licenses, or experience. When these qualifications are made tougher, the number of qualified workers will decrease at any given wage. On the other hand, the government may also subsidize training or even reduce the required level of qualifications. For example, government might offer subsidies for nursing schools or nursing students. Such provisions would shift the supply curve of nurses to the right. In addition, government policies that change the relative desirability of working versus not working also affect the labor supply. These include unemployment benefits, maternity leave, child care benefits, and welfare policy. For example, child care benefits may increase the labor supply of working mothers. Long term unemployment benefits may discourage job searching for unemployed workers. 

## t03 (paraphrase)
**Câu hỏi:** What is the name for a product that people buy less of after their earnings go up?

**Đáp án chuẩn / hành vi mong đợi:** An inferior good: its demand falls when income rises (the demand curve shifts left).

**Agent (answered):** A product whose demand falls when income rises (and rises when income falls) is called an inferior good. [micro3e-p0069-pb1000-000]

> **[micro3e-p0069-pb1000-000]** (trang 69)
>
> generic brand groceries and more name brand groceries. They are less likely to buy used cars and more likely to buy new cars. They will be less likely to rent an apartment and more likely to own a home. A product whose demand falls when income rises, and vice versa, is called an inferior good. In other words, when income increases, the demand curve shifts to the left.

## t04 (direct)
**Câu hỏi:** In the movie theater example, what price floor does the city set and how many people attend movies afterwards?

**Đáp án chuẩn / hành vi mong đợi:** A price floor of $12 per ticket; attendance (quantity demanded) falls from 1,800 to 1,400.

**Agent (answered):** In the movie theater example, the city government imposes a price floor of $12 per movie ticket. As a result, the quantity demanded of movie tickets falls to 1,400 people attending movies, down from 1,800 at the $8 equilibrium. [micro3e-p0088-pb1000-003]

> **[micro3e-p0088-pb1000-003]** (trang 88)
>
> Figure 3.24 (b) shows a price floor example using a string of struggling movie theaters, all in the same city. The current equilibrium is $8 per movie ticket, with 1,800 people attending movies. The original consumer surplus is G + H + J, and producer surplus is I + K. The city government is worried that movie theaters will go out of business, reducing the entertainment options available to citizens, so it decides to impose a price floor of $12 per ticket. As a result, the quantity demanded of movie tickets falls to 1,400. The new consumer surplus is G, and the new producer surplus is H + I. In effect, the price floor causes the area H to be transferred from consumer to producer surplus, but also causes a deadweight loss of J + K.

## t05 (conditional)
**Câu hỏi:** For the monopsony wage schedule in Table 14.5, what is the marginal cost of labor when the firm goes from three to four workers, and why is it higher than the wage?

**Đáp án chuẩn / hành vi mong đợi:** $7 (wage $4 per hour, total cost rises from $9 to $16); it exceeds the wage because hiring one more worker requires raising the wage for all previous hires too.

**Agent (answered):** Going from three to four workers, the marginal cost of labor is $7 per hour (total cost rises from $9 to $16), while the wage at four workers is $4 per hour [micro3e-p0344-pb1000-000]. It is higher than the wage because hiring one more worker requires raising the wage paid to all workers, not just the new hire, so the extra cost includes the higher wage for every previous hire as well [micro3e-p0344-pb1000-000].

> **[micro3e-p0344-pb1000-000]** (trang 344)
>
> example in Table 14.5.
> 
> Supply of Labor 1 2 3 4 5
> 
> Wage Rate $1 per hour $2 per hour $3 per hour $4 per hour $5 per hour
> 
> Total Cost of Labor $1 $4 $9 $16 $25
> 
> Marginal Cost of Labor $1 $3 $5 $7 $9
> 
> TABLE 14.5 The Marginal Cost of Labor
> 
> There are a couple of things to notice from the table. First, the marginal cost increases faster than the wage rate. In fact, for any number of workers more than one, the marginal cost of labor is greater than the wage. This is because to hire one more worker requires paying a higher wage rate, not just for the new worker but for all the previous hires also. We can see this graphically in Figure 14.7.

## t06 (paraphrase)
**Câu hỏi:** What explanations have economists offered for why a much smaller share of American workers are in labor organizations than in the 1950s?

**Đáp án chuẩn / hành vi mong đợi:** Four: the shift from manufacturing to services; globalization and foreign competition; less desire for unions because of workplace protection laws; a U.S. legal environment that makes organizing harder.

**Agent (answered):** Economists have offered four possible explanations for the decline in the share of U.S. workers in unions since the early 1950s: the shift from manufacturing to service industries, globalization and increased competition from foreign producers, a reduced desire for unions because of workplace protection laws now in place, and a U.S. legal environment that makes it relatively more difficult for unions to organize and expand [micro3e-p0350-pb1000-000]. The manufacturing-to-service shift matters because unions were historically stronger in manufacturing, and job growth occurred where unions were not [micro3e-p0350-pb1000-001].

> **[micro3e-p0350-pb1000-000]** (trang 350)
>
> The Decline in U.S. Union Membership
> 
> The proportion of U.S. workers belonging to unions has declined dramatically since the early 1950s. Economists have offered a number of possible explanations:
> 
> • The shift from manufacturing to service industries • The force of globalization and increased competition from foreign producers • A reduced desire for unions because of the workplace protection laws now in place • U.S. legal environment that makes it relatively more difficult for unions to organize workers and expand their membership
> 
> Let's discuss each of these four explanations in more detail.

> **[micro3e-p0350-pb1000-001]** (trang 350)
>
> A first possible explanation for the decline in the share of U.S. workers belonging to unions involves the patterns of job growth in the manufacturing and service sectors of the economy as Figure 14.13 shows. The U.S. economy had about 15 million manufacturing jobs in 1960. This total rose to 19 million by the late 1970s and then declined to 17 million in 2013. Meanwhile, the number of jobs in service industries (including government employment) rose from 35 million in 1960 to over 118 million by 2013, according to the Bureau of Labor Statistics. Because over time unions were stronger in manufacturing than in service industries, the growth in jobs was not happening where the unions were. It is interesting to note that government workers comprise several of the biggest unions in the country, including the American Federation of State, County and Municipal Employees (AFSCME); the Service Employees International Union; and the National Education Association. 

## t07 (filter, filter {"chapter": 14})
**Câu hỏi:** Which law set up the minimum wage and the overtime pay rule?

**Đáp án chuẩn / hành vi mong đợi:** The Fair Labor Standards Act of 1938 (also limits child labor; overtime for hourly jobs beyond 40 hours per week).

**Agent (answered):** The Fair Labor Standards Act of 1938 established the minimum wage and the rules requiring overtime pay for hourly jobs that exceed 40 hours per week [micro3e-p0342-pb1000-001].

> **[micro3e-p0342-pb1000-001]** (trang 342)
>
> Table 14.4 lists some prominent U.S. workplace protection laws. Many of the laws listed in the table were only the start of labor market regulations in these areas and have been followed, over time, by other related laws, regulations, and court rulings.
> 
> Law Protection
> 
> Establishes procedures for establishing a union that firms are obligated to follow; sets up the National Labor Relations Board for deciding disputes
> 
> National Labor- Management Relations Act of 1935 (the "Wagner Act")
> 
> Social Security Act of 1935
> 
> Under Title III, establishes a state-run system of unemployment insurance, in which workers pay into a state fund when they are employed and received benefits for a time when they are unemployed
> 
> Fair Labor Standards Act of 1938
> 
> Establishes the minimum wage, limits on child labor, and rules requiring payment of overtime pay for those in jobs that are paid by the hour and exceed 40 hours per week
> 
> Taft-Hartley Act of 1947

## t08 (filter, filter {"chapter": 3})
**Câu hỏi:** What happens in a market when the price sits below the equilibrium level?

**Đáp án chuẩn / hành vi mong đợi:** Excess demand (a shortage): quantity demanded exceeds quantity supplied (gasoline buyers mob stations, stations run short), and the price rises toward equilibrium.

**Agent (answered):** When the price is below equilibrium, quantity demanded exceeds quantity supplied, creating excess demand, or a shortage: the lower price stimulates demand and depresses supply. Buyers compete for the limited product (e.g., gas stations running short), and sellers recognize they can earn higher profits by raising the price, so the price rises toward the equilibrium level. [micro3e-p0066-pb1000-000] [micro3e-p0064-pb1000-002]

> **[micro3e-p0066-pb1000-000]** (trang 66)
>
> When the price is below equilibrium, there is excess demand, or a shortage-that is, at the given price the quantity demanded, which has been stimulated by the lower price, now exceeds the quantity supplied, which has been depressed by the lower price. In this situation, eager gasoline buyers mob the gas stations, only to find many stations running short of fuel. Oil companies and gas stations recognize that they have an opportunity to make higher profits by selling what gasoline they have at a higher price. As a result, the price rises toward the equilibrium level. Read Demand, Supply, and Efficiency for more discussion on the importance of the demand and supply model.

> **[micro3e-p0064-pb1000-002]** (trang 64)
>
> FIGURE 3.4 Demand and Supply for Gasoline The demand curve (D) and the supply curve (S) intersect at the
> 
> equilibrium point E, with a price of $1.40 and a quantity of 600. The equilibrium price is the only price where quantity demanded is equal to quantity supplied. At a price above equilibrium like $1.80, quantity supplied exceeds the quantity demanded, so there is excess supply. At a price below equilibrium such as $1.20, quantity demanded exceeds quantity supplied, so there is excess demand.
> 
> Price (per gallon) Quantity demanded (millions of gallons) Quantity supplied (millions of gallons)
> 
> $1.00 800 500
> 
> $1.20 700 550
> 
> $1.40 600 600
> 
> TABLE 3.3 Price, Quantity Demanded, and Quantity Supplied

## t09 (multi_hop)
**Câu hỏi:** What does the Fair Labor Standards Act require, and how could laws like it help explain the decline in union membership?

**Đáp án chuẩn / hành vi mong đợi:** It establishes the minimum wage, limits child labor and requires overtime pay; such workplace protection laws reduce workers' desire for unions, one explanation for declining membership.

**Agent (abstain):** The retrieved passages do not describe the Fair Labor Standards Act or what it requires, so I cannot answer the first part of the question from the textbook. The passages only offer, as one explanation for declining union membership, that workers may have a "reduced desire for unions because of the workplace protection laws now in place" [micro3e-p0350-pb1000-000]. That supports the general idea that protective laws may reduce demand for unions, but it does not name or explain the FLSA specifically. I did not use outside knowledge to fill the gap.

## t10 (multi_hop)
**Câu hỏi:** What share of bachelor's degrees did women earn in the 2018-19 academic year, and how much more does a bachelor's degree holder earn over a career than a typical high school graduate?

**Đáp án chuẩn / hành vi mong đợi:** Women earned 57% of bachelor's degrees; bachelor's holders earn about $2.8 million over their careers, $1.2 million more than the median high-school-diploma worker.

**Agent (answered):** Women earned 57% of bachelor's degrees in the 2018-19 academic year [micro3e-p0355-pb1000-004]. A bachelor's degree holder earns an average of $2.8 million over a career, which is $1.2 million more than the median for workers with a high school diploma, according to a 2021 Georgetown University Center on Education and the Workforce report [micro3e-p0362-pb1000-002].

> **[micro3e-p0355-pb1000-004]** (trang 355)
>
> Investigating the Female/Male Earnings Gap
> 
> As a result of changes in law and culture, women began to enter the paid workforce in substantial numbers in the mid- to late-twentieth century. As of February 2022, 56.0% of women aged 20 and over held jobs, while 67.6% of men aged 20 and over did. Moreover, along with entering the workforce, women began to ratchet up their education levels. In 1971, 44% of undergraduate college degrees went to women. As of the 2018-19 academic year, women earned 57% of bachelor's degrees. In 1970, women received 5.4% of the degrees from law schools and 8.4% of the degrees from medical schools. By 2017, women were receiving just over 50% of the law degrees, and by 2019, 48% of the medical degrees. There are now slightly more women than men in both law schools and medical schools. These gains in education and experience have reduced the female/male wage gap over time. 

> **[micro3e-p0362-pb1000-002]** (trang 362)
>
> The Increasing Value of a College Degree The cost of college has increased dramatically in recent decades, causing many college students to take student loans to afford it. Despite this, the value of a college degree has never been higher. How can we explain this?
> 
> We can estimate the value of a bachelor's degree as the difference in lifetime earnings between the average holder of a bachelor's degree and the average high school graduate. According to a 2021 report from the Georgetown University Center on Education and the Workforce, adults with a bachelor's degree earn an average of $2.8 million during their careers, $1.2 million more than the median for workers with a high school diploma. College graduates also have a significantly lower unemployment rate than those with lower educational attainments.

## t11 (conditional)
**Câu hỏi:** In the credit card market example, if the interest rate is 13%, how large is the gap between the funds borrowers want and the funds lenders offer?

**Đáp án chuẩn / hành vi mong đợi:** Borrowers demand $700 billion but lenders supply only $510 billion: a shortage of $190 billion (the rate tends to rise toward the 15% equilibrium).

**Agent (answered):** At a 13% interest rate, borrowers demand $700 billion while credit card firms supply only $510 billion, so the gap (excess demand, or shortage of funds) is $190 billion. [micro3e-p0108-pb1000-003]

> **[micro3e-p0108-pb1000-003]** (trang 108)
>
> If the interest rate is below the equilibrium, then excess demand or a shortage of funds occurs in this market. At an interest rate of 13%, the quantity of funds credit card borrowers demand increases to $700 billion, but the quantity credit card firms are willing to supply is only $510 billion. In this situation, credit card firms will perceive that they are overloaded with eager borrowers and conclude that they have an opportunity to raise interest rates or fees. The interest rate will face economic pressures to creep up toward the equilibrium level.
> 
> The FRED database publishes some two dozen measures of interest rates, including interest rates on credit cards, automobile loans, personal loans, mortgage loans, and more. You can find these at the FRED website (https://openstax.org/l/FRED_stlouis).

## ut1 (unanswerable)
**Câu hỏi:** By what percentage did demand for laptops fall when tablet computers became cheaper?

**Đáp án chuẩn / hành vi mong đợi:** TỪ CHỐI — p69 says only that laptop demand decreased (leftward shift); no percentage or quantity is given.

**Agent (abstain):** The retrieved passages say that as tablet prices fell, demand for laptops decreased, shown as a leftward shift in the laptop demand curve [micro3e-p0069-pb1000-004]. However, no passage gives a percentage by which laptop demand fell, so the specific number asked for is not in the textbook excerpts I could retrieve.

## ut2 (unanswerable)
**Câu hỏi:** How large is the union wage premium in Canada according to the chapter?

**Đáp án chuẩn / hành vi mong đợi:** TỪ CHỐI — Canada is mentioned for union formation rules (p352) and immigration (p362), never for union wages.

**Agent (abstain):** The retrieved passages do not give a union wage premium figure for Canada. The only Canada reference (micro3e-p0352-pb1000-002) says forming unions is easier in Canada than in the United States, and the union-membership table covers only Austria, France, Germany, Japan, the Netherlands, Spain, Sweden, the UK and the US. I had one search available, and it returned no Canada-specific wage premium number.

## ut3 (unanswerable)
**Câu hỏi:** How many members did the United Auto Workers have in 1960?

**Đáp án chuẩn / hành vi mong đợi:** TỪ CHỐI — p351 gives UAW membership only for 1985 (975,000) and 2015 (about 390,000); p346 gives 408,000 for 2021. No 1960 figure.

**Agent (abstain):** The retrieved passages give UAW membership for 1985 (975,000) and 2015 (about 390,000) and 2021 (408,000), but do not state the UAW membership in 1960.

## ut4 (unanswerable)
**Câu hỏi:** What is the unemployment rate of U.S. college graduates according to the chapter?

**Đáp án chuẩn / hành vi mong đợi:** TỪ CHỐI — p362 only says college graduates have 'a significantly lower unemployment rate'; no rate is given anywhere in the corpus.

**Agent (abstain):** The retrieved passages say college graduates have a "significantly lower unemployment rate than those with lower educational attainments" [micro3e-p0362-pb1000-002], but they never give a numerical unemployment rate for U.S. college graduates. I could not find the specific figure, so I cannot answer the question as asked.

