# IFA policy audit

The National Health Mission AMB operational guideline separates the two
phases in one row: daily one red IFA tablet starts from the fourth month of
pregnancy (second trimester), continues through pregnancy for a minimum of 180
days, and then continues for 180 days postpartum for lactating mothers with a
0–6 month child.

HAVEN GRID stores those as two `IFADoseRule` records on the IFA Red item:

* `ifa-red-antenatal`: quantity 1 tablet, daily, pregnant women, antenatal from
  the fourth month, duration 180 days;
* `ifa-red-postpartum`: quantity 1 tablet, daily, lactating mothers with a
  0–6 month child, postpartum continuation, duration 180 days.

The basis reference is the [AMB Operational Guidelines](https://nhm.gov.in/images/pdf/Nutrition/AMB-guidelines/Anemia-Mukt-Bharat-Operational-Guidelines-FINAL.pdf). Any forecast bucket allocation remains a kernel-derived calculation and is not stored as policy text.
