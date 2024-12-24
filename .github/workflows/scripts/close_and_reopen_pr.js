module.exports = (async function ({github, context}) {
    const pr_number = process.env.PR_NUMBER;
    const pr_operation = process.env.PR_OPERATION;
    let sleep_time = 0;

    if (!['created', 'updated'].includes(pr_operation)) {
        console.log('PR was not created as there were no changes.')
        return;
    }

    for (const new_state of ['closed', 'open']) {
        // some sleep time needed to make sure API handles open after close
        if (sleep_time)
            await new Promise(r => setTimeout(r, sleep_time));

        github.rest.issues.update({
            issue_number: pr_number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            state: new_state
        });

        sleep_time = 2000;
    }
})
