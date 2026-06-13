import { Router, type IRouter } from "express";
import healthRouter from "./health";
import initiativesRouter from "./initiatives";
import dashboardRouter from "./dashboard";
import departmentsRouter from "./departments";

const router: IRouter = Router();

router.use(healthRouter);
router.use(initiativesRouter);
router.use(dashboardRouter);
router.use(departmentsRouter);

export default router;
