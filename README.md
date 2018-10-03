# compogit
Poor man's git submodules

This project is basically about playing around with `git rebase -i`.

[sic](https://github.com/HeidiWindkraft/sic) has some components which are ready to be pushed,
while other components aren't.
Unfortunately I committed change sets which contain changes in multiple components.
As git works based on commits, you can't just push half of a commit or only a directory.
Therefore, the commits have to be split using `git rebase -i`.
`compogit` is meant to automate this.

If you have different components in your repository,
you should probably create a git repository for each component.
