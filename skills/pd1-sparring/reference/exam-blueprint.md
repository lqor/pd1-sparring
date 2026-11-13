# Exam blueprint

Source: the official Salesforce Certified Platform Developer Exam Guide on Salesforce Help
(https://help.salesforce.com/s/articleView?id=005298965&type=1). Read on 13 November 2026.
If you have web access, re-read the guide at the start of a learner's first session and tell
them if anything below has changed, especially the Version line.

## The facts

| | |
|---|---|
| Credential name | Salesforce Certified Platform Developer (still widely called Platform Developer I or PD1) |
| Questions | 60 scored multiple-choice questions, plus up to 5 unscored ones mixed in |
| Time | 105 minutes |
| Passing score | 68% (41 of 60) |
| Version | Questions align to the Summer '25 release |
| Fee | US$200, retake US$100, plus tax |
| Delivery | Proctored, at a test centre or online |
| References allowed | None |
| Prerequisite | None. It is itself the prerequisite for Platform Developer II |

105 minutes for up to 65 questions is about 95 seconds each. Unscored questions are not marked,
so every question deserves a real answer.

## Sections and weights

| Section | Weight | About how many of 60 |
|---|---|---|
| Developer Fundamentals | 27% | 16 |
| Process Automation and Logic | 28% | 17 |
| User Interface | 25% | 15 |
| Testing, Debugging, and Deployment | 20% | 12 |

Salesforce reports a percentage per section after the exam, not a total.

## Objectives, as the guide words them

**Developer Fundamentals (27%)**
- Understand multi-tenant concepts and design frameworks, such as MVC architecture and Lightning Component Framework.
- Given a scenario, identify common use cases and best practices for declarative versus programmatic customizations, including governor limits, formula fields, and roll-up summaries.
- Given a scenario, determine, create, and access the appropriate data model including objects, fields, relationships, and external IDs.
- Understand use cases and limitations of using Agentforce for Developers.

**Process Automation and Logic (28%)**
- Identify the capabilities of the declarative process automation features.
- Understand how to declare variables, constants, methods, modifiers, Apex interfaces, and the appropriate use cases for each.
- Given a scenario, assess how Apex control flow statements will execute and when to apply different control flow statements.
- Given a scenario, write SOSL, SOQL, and DML statements in Apex, and assess what they will return.
- Given a scenario, follow best practices to write Apex classes and triggers.
- Given a scenario, understand governor limits and their implications on Apex transactions.
- Describe the relationship between Apex transactions, the save order of execution, and the potential for recursion and/or cascading.
- Implement exception handling in Apex, including custom exceptions as needed.
- Given a scenario, use declarative functionality and Apex together to automate business logic.

**User Interface (25%)**
- Given a scenario, prevent user interface and data access security vulnerabilities.
- Given a scenario, display and use custom user interface components, including Lightning components, Flow, and Visualforce.
- Describe the use cases and best practices for Lightning Web Components, including the framework, benefits, and events.
- Given a scenario, implement Apex to work with various types of page components, including Lightning components, Flow, and Agentforce.

**Testing, Debugging, and Deployment (20%)**
- Write and execute tests for triggers, controllers, classes, and flows using various sources of test data.
- Given a scenario, know how and when to use the Salesforce Developer tools such as Salesforce DX, Salesforce CLI, and Developer Console.
- Describe how to approach debugging system issues and monitoring flows, performance, asynchronous, and batch jobs.
- Describe the environments, requirements, and process for deploying code and associated configurations.

## What the guide says is out of scope

Administering standard applications, mobile app development, publishing managed packages on
AppExchange, tuning, and designing integrations such as callouts, APIs and email services.
Callouts still show up at the edges (async Apex, test mocks), but integration design does not.

## How to use the weights

- No section can be skipped. Scoring 0% on the lightest section (20%) leaves a ceiling of 80%.
- A 10-point gain in a section is worth about 2 to 3 points overall. Process Automation and Logic and
  Developer Fundamentals move the total most.
- User Interface is where many people from an admin background lose the exam, because it mixes three
  UI technologies. It rewards recognition (which tool, which decorator, which controller type) far more
  than the ability to build pages. Do not try to learn LWC, Aura and Visualforce deeply for this exam.
- A version line of Summer '25 means: when newer releases change a default or add a feature, the exam
  still expects the Summer '25 behaviour until Salesforce updates this guide.

## Recommended official material (free)

- Trailhead trail: Study for the Platform Developer Exam
- Trailmix: Prepare for Your Salesforce Platform Developer Certification
- Apex Developer Guide, especially: Apex Transactions and Governor Limits; Triggers and Order of Execution
- Lightning Web Components Developer Guide
- SOQL and SOSL Reference
