Regenerate all project-templates from their bundles.

Run the following three commands sequentially (each depends on the previous succeeding):

```bash
./setup-project.sh project-templates/minimal --bundle minimal --update && \
./setup-project.sh project-templates/quant --bundle quant --update && \
./setup-project.sh project-templates/webdev --bundle webdev --update
```

After all three complete, report a summary:
- Which templates were regenerated
- How many components were installed in each
- Any warnings or failures from the output

If any command fails, stop and report the error — do not continue to the next template.
